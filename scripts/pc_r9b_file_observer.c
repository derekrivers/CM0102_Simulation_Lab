#define _GNU_SOURCE
#define _LARGEFILE64_SOURCE
#include <dlfcn.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <linux/audit.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <signal.h>
#include <stddef.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/prctl.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <unistd.h>

/* Original metadata-only observer. Qualified identity depends on a successfully
 * installed single-task policy, never on pre/post fstat equality alone. */
#define ROW_CAP 2048u
#define PATH_CAP 1024u
#define ABNORMAL_CAP 1024u
#define OUTPUT_CAP (16u*1024u*1024u)
static int trace_fd = -1, active;
static uint64_t events, errors, rows_used, abnormal_count, output_bytes;
static const char *clean_root;
static __thread unsigned depth;
static __thread uint64_t previous_mask;
struct identity { uint64_t dev, ino; int64_t size; int known; char path[PATH_CAP]; };
struct row {
    struct identity id;
    char op[24], supplied[PATH_CAP];
    int ok, error;
    uint64_t calls, positive, requested, delivered_lower, items, nested, short_items;
};
static struct row rows[ROW_CAP];
static char abnormalities[ABNORMAL_CAP][4500];
#define DECL(ret,n,args) static ret (*real_##n) args
DECL(int,open,(const char *,int,...));
DECL(int,open64,(const char *,int,...));
DECL(int,openat,(int,const char *,int,...));
DECL(int,openat64,(int,const char *,int,...));
DECL(FILE *,fopen,(const char *,const char *));
DECL(FILE *,fopen64,(const char *,const char *));
DECL(ssize_t,read,(int,void *,size_t));
DECL(ssize_t,pread,(int,void *,size_t,off_t));
DECL(ssize_t,pread64,(int,void *,size_t,off64_t));
DECL(size_t,fread,(void *,size_t,size_t,FILE *));
DECL(size_t,fread_unlocked,(void *,size_t,size_t,FILE *));
DECL(void *,mmap,(void *,size_t,int,int,int,off_t));
DECL(void *,mmap64,(void *,size_t,int,int,int,off64_t));
#define RESOLVE(n) do { if (!real_##n) { *(void **)(&real_##n)=dlsym(RTLD_NEXT,#n); if (!real_##n) _exit(125); } } while(0)
static void add(uint64_t *n,uint64_t value) {
    if (UINT64_MAX-*n < value) { errors=1; return; }
    *n += value;
}
static uint64_t product(uint64_t a,uint64_t b) {
    if (a && b>UINT64_MAX/a) { errors=1; return 0; }
    return a*b;
}
static void enter(void) {
    int e=errno;
    if (active) {
        uint64_t mask=UINT64_MAX, old;
        /* Mask BEFORE publishing depth. Raw kernel mask also covers the NPTL
         * signals silently excluded by glibc sigprocmask. x86-64 has 64 bits. */
        if (syscall(SYS_rt_sigprocmask,SIG_BLOCK,&mask,&old,sizeof mask)) _exit(120);
        if (depth++==0) previous_mask=old;
    }
    errno=e;
}
static void leave(int e) {
    if (active && --depth==0 &&
        syscall(SYS_rt_sigprocmask,SIG_SETMASK,&previous_mask,NULL,sizeof previous_mask)) _exit(119);
    errno=e;
}static struct identity inspect(int fd) {
    struct identity id={0};
    if (fd<0) return id;
    char path[64];struct stat st;
    snprintf(path,sizeof path,"/proc/self/fd/%d",fd);
    ssize_t n=syscall(SYS_readlink,path,id.path,sizeof id.path-1);
    if (n<0 || n>=(ssize_t)sizeof id.path-1 || syscall(SYS_fstat,fd,&st)) return id;
    id.path[n]=0;id.dev=st.st_dev;id.ino=st.st_ino;id.size=st.st_size;id.known=1;
    return id;
}
static int equal(const struct identity *a,const struct identity *b) {
    return a->known==b->known && a->dev==b->dev && a->ino==b->ino &&
        a->size==b->size && !strcmp(a->path,b->path);
}
static int hex(char *out,size_t cap,const char *in) {
    static const char h[]="0123456789abcdef";size_t i=0;
    if (!in) in="";
    while(in[i] && i*2+2<cap) {unsigned char c=in[i];out[i*2]=h[c>>4];out[i*2+1]=h[c&15];i++;}
    out[i*2]=0;return in[i]!=0;
}
static void emit(const char *op,int fd,int ok,uint64_t delivered,uint64_t requested,
                 uint64_t items,int short_items,int e,const char *supplied,
                 const struct identity *before) {
    if (!active) return;
    int saved=errno;struct identity id=inspect(fd);
    add(&events,1);
    if (((ok || delivered) && fd>=0 && !id.known) || (before && (ok || delivered) && !equal(before,&id))) errors=1;
    if (!supplied) supplied="";
    size_t plen=strnlen(supplied,PATH_CAP);
    if (plen==PATH_CAP) {errors=1;plen=PATH_CAP-1;}
    unsigned index;
    for(index=0;index<rows_used;index++) {
        struct row *r=&rows[index];
        if (!strcmp(r->op,op) && r->ok==ok && r->error==(ok?0:e) &&
            equal(&r->id,&id) && !strncmp(r->supplied,supplied,PATH_CAP)) break;
    }
    if (index==rows_used) {
        if (rows_used==ROW_CAP) {errors=1;errno=saved;return;}
        rows_used++;struct row *r=&rows[index];r->id=id;r->ok=ok;r->error=ok?0:e;
        snprintf(r->op,sizeof r->op,"%s",op);memcpy(r->supplied,supplied,plen);r->supplied[plen]=0;
    }
    struct row *r=&rows[index];add(&r->calls,1);add(&r->positive,delivered>0);
    add(&r->requested,requested);add(&r->delivered_lower,delivered);add(&r->items,items);
    add(&r->nested,depth>1);add(&r->short_items,short_items);
    size_t rootlen=strlen(clean_root);
    int outside=id.known && (strncmp(id.path,clean_root,rootlen) || id.path[rootlen]!='/');
    if (!ok || (!id.known && fd>=0) || outside) {
        if (abnormal_count==ABNORMAL_CAP) errors=1;
        else {
            char target[PATH_CAP*2],given[PATH_CAP*2];
            if (hex(target,sizeof target,id.path) || hex(given,sizeof given,r->supplied)) errors=1;
            int n=snprintf(abnormalities[abnormal_count],4500,
                "A\t%"PRIu64"\t%u\t%d\t%"PRIu64"\t%"PRIu64"\t%d\t%s\t%s\n",
                events,index,fd,requested,delivered,e,target,given);
            if(n<0 || n>=4500) errors=1;else abnormal_count++;
        }
    }
    errno=saved;
}
static void write_line(const char *s) {
    size_t n=strlen(s);
    if (output_bytes+n>OUTPUT_CAP-256) {errors=1;return;}
    ssize_t w=syscall(SYS_write,trace_fd,s,n);
    if(w!=(ssize_t)n) {errors=1;return;}output_bytes+=n;
}
static void single_task_policy(void) {
#if !defined(__x86_64__)
#error R9b qualified only on x86-64 Linux
#endif
    struct sock_filter code[]={
        BPF_STMT(BPF_LD|BPF_W|BPF_ABS,offsetof(struct seccomp_data,arch)),
        BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,AUDIT_ARCH_X86_64,1,0),
        BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_KILL_PROCESS),
        BPF_STMT(BPF_LD|BPF_W|BPF_ABS,offsetof(struct seccomp_data,nr)),
        BPF_JUMP(BPF_JMP|BPF_JSET|BPF_K,0x40000000,0,1),
        BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_KILL_PROCESS),
        BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,SYS_clone,0,1),
        BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_KILL_PROCESS),
        BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,SYS_clone3,0,1),
        BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_KILL_PROCESS),
        BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,SYS_fork,0,1),
        BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_KILL_PROCESS),
        BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,SYS_vfork,0,1),
        BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_KILL_PROCESS),
        BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ALLOW)
    };
    struct sock_fprog program={sizeof code/sizeof code[0],code};
    if(prctl(PR_SET_NO_NEW_PRIVS,1,0,0,0) ||
       syscall(SYS_seccomp,SECCOMP_SET_MODE_FILTER,SECCOMP_FILTER_FLAG_TSYNC,&program)!=0) _exit(118);
    /* After TSYNC, every existing task is filtered and no new task can appear. */
    DIR *d=opendir("/proc/self/task");if(!d)_exit(117);
    unsigned count=0;struct dirent *entry;
    errno=0;while((entry=readdir(d))) if(entry->d_name[0]!='.')count++;
    int e=errno;closedir(d);if(e || count!=1)_exit(116);
}
__attribute__((constructor)) static void begin(void) {
    const char *path=getenv("PC_R9B_TRACE");if(!path)return;
    if(getenv("PC_R9B_WAIT_FOR_STACK_REEXEC") && !getenv("RECOMP_STACK_SET"))return;
    clean_root=getenv("PC_R9B_CLEAN_ROOT");if(!clean_root || !*clean_root)_exit(115);
    trace_fd=syscall(SYS_openat,AT_FDCWD,path,O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC|O_NOFOLLOW,0600);
    if(trace_fd<0)_exit(124);
    write_line("PCR9BFILE1\n");single_task_policy();
    write_line("POLICY\tx86_64-tsync-single-task-no-clone-v1\n");active=1;
}
__attribute__((destructor)) static void finish(void) {
    if(!active)return;
    enter();active=0;
    for(unsigned i=0;i<rows_used;i++) {
        struct row *r=&rows[i];char target[PATH_CAP*2],given[PATH_CAP*2],line[4600];
        if(hex(target,sizeof target,r->id.path)||hex(given,sizeof given,r->supplied))errors=1;
        int n=snprintf(line,sizeof line,
            "R\t%u\t%s\t%d\t%d\t%d\t%"PRIu64"\t%"PRIu64"\t%"PRId64
            "\t%"PRIu64"\t%"PRIu64"\t%"PRIu64"\t%"PRIu64"\t%"PRIu64
            "\t%"PRIu64"\t%"PRIu64"\t%s\t%s\n",i,r->op,r->ok,r->error,r->id.known,
            r->id.dev,r->id.ino,r->id.size,r->calls,r->positive,r->requested,
            r->delivered_lower,r->items,r->nested,r->short_items,target,given);
        if(n<0 || n>=(int)sizeof line)errors=1;else write_line(line);
    }
    for(unsigned i=0;i<abnormal_count;i++)write_line(abnormalities[i]);
    char footer[256];int n=snprintf(footer,sizeof footer,
        "PCR9BDONE\t%"PRIu64"\t%"PRIu64"\t%"PRIu64"\t%"PRIu64"\n",events,rows_used,abnormal_count,errors);
    if(n<0 || syscall(SYS_write,trace_fd,footer,(size_t)n)!=n || syscall(SYS_fsync,trace_fd))_exit(122);
    syscall(SYS_close,trace_fd);trace_fd=-1;
    if(syscall(SYS_rt_sigprocmask,SIG_SETMASK,&previous_mask,NULL,sizeof previous_mask))_exit(119);
}
static int needs_mode(int flags){return(flags&O_CREAT)||((flags&O_TMPFILE)==O_TMPFILE);}
#define OPEN_WRAP(n) \
int n(const char *p,int flags,...) { RESOLVE(n); mode_t m=0; \
 if(needs_mode(flags)){va_list a;va_start(a,flags);m=va_arg(a,mode_t);va_end(a);} \
 enter();int r=real_##n(p,flags,m);int e=errno;emit(#n,r,r>=0,0,0,0,0,e,p,NULL);leave(e);return r; }
OPEN_WRAP(open)
OPEN_WRAP(open64)
#define OPENAT_WRAP(n) \
int n(int dir,const char *p,int flags,...) { RESOLVE(n);mode_t m=0; \
 if(needs_mode(flags)){va_list a;va_start(a,flags);m=va_arg(a,mode_t);va_end(a);} \
 enter();int r=real_##n(dir,p,flags,m);int e=errno;emit(#n,r,r>=0,0,0,0,0,e,p,NULL);leave(e);return r; }
OPENAT_WRAP(openat)
OPENAT_WRAP(openat64)
#define FOPEN_WRAP(n) \
FILE *n(const char *p,const char *mode){RESOLVE(n);enter();FILE *r=real_##n(p,mode);int e=errno; \
 emit(#n,r?fileno(r):-1,r!=NULL,0,0,0,0,e,p,NULL);leave(e);return r;}
FOPEN_WRAP(fopen)
FOPEN_WRAP(fopen64)
ssize_t read(int fd,void *b,size_t count){RESOLVE(read);enter();struct identity before=inspect(fd);
 ssize_t r=real_read(fd,b,count);int e=errno;
 emit("read",fd,r>=0,r>0?(uint64_t)r:0,count,0,0,e,NULL,&before);leave(e);return r;}
#define PREAD_WRAP(n,t) \
ssize_t n(int fd,void *b,size_t count,t offset){RESOLVE(n);enter();struct identity before=inspect(fd); \
 ssize_t r=real_##n(fd,b,count,offset);int e=errno; \
 emit(#n,fd,r>=0,r>0?(uint64_t)r:0,count,0,0,e,NULL,&before);leave(e);return r;}
PREAD_WRAP(pread,off_t)
PREAD_WRAP(pread64,off64_t)
#define FREAD_WRAP(n) \
size_t n(void *b,size_t size,size_t count,FILE *f){RESOLVE(n);enter();int fd=fileno(f); \
 struct identity before=inspect(fd);size_t r=real_##n(b,size,count,f);int e=errno; \
 emit(#n,fd,!ferror(f),product(r,size),product(size,count),r,size>1&&r<count,e,NULL,&before);leave(e);return r;}
FREAD_WRAP(fread)
FREAD_WRAP(fread_unlocked)
#define MMAP_WRAP(n,t) \
void *n(void *a,size_t len,int prot,int flags,int fd,t offset){RESOLVE(n);enter(); \
 struct identity before=inspect(fd);void *r=real_##n(a,len,prot,flags,fd,offset);int e=errno; \
 emit(#n,(flags&MAP_ANONYMOUS)?-1:fd,r!=MAP_FAILED,0,len,0,0,e,NULL,(flags&MAP_ANONYMOUS)?NULL:&before);leave(e);return r;}
MMAP_WRAP(mmap,off_t)
MMAP_WRAP(mmap64,off64_t)