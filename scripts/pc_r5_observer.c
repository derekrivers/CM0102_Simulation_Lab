/* Independent private research observer; no translated code or game data.
 * Link against pinned Bosman with --wrap=f_005cde40. */
#define _POSIX_C_SOURCE 200809L
#include "rt.h"
#include "rt_host.h"
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
static int seen;
static unsigned total;
static int valid(uint32_t a, uint32_t n)
{
    uint64_t end = (uint64_t)a+n;
    return n && ((a>=rt_image_base() &&
        end<=(uint64_t)rt_image_base()+rt_image_size()) ||
        (a>=RT_HEAP_BASE && end<=rt_heap_top()));
}
static int put(int fd,const void *p,size_t n)
{
    const char *b=p;
    while(n) {
        ssize_t k=write(fd,b,n);
        if(k<0 && errno==EINTR) continue;
        if(k<=0) return 0;
        b+=k; n-=(size_t)k;
    }
    return 1;
}
static int range(int fd,uint32_t a,uint32_t n)
{
    uint32_t h[2]={a,n};
    if(!valid(a,n) || n>8388608 || total>16777216-n) return 0;
    total+=n;
    return put(fd,h,sizeof h) && put(fd,g_mem+a,n);
}
static int word(uint32_t a,uint32_t *out)
{
    if(!valid(a,4)) return 0;
    *out=rd32(g_mem,a); return 1;
}
static int capture(int fd)
{
    const uint32_t globals[]={0xae235c,0xae2350,0xae2364,0xae23b4,
        0xae23bc,0xde1d08,0xb63c98,0xae2c90};
    uint32_t clubs,nations,staff,cb,sb,ctx,reg;
    uint32_t first,nf,second,ns,mapping,rows,nr;
    if(!word(globals[0],&clubs) || !word(globals[1],&nations) ||
       !word(globals[2],&staff) || !word(globals[3],&cb) ||
       !word(globals[4],&sb) || !word(globals[5],&ctx) ||
       !word(globals[6],&reg) ||
       clubs<1 || clubs>10000 || nations>clubs/2 ||
       staff<16 || staff>100000 || !valid(ctx,0x605) ||
       !word(ctx+0x5f9,&first) || !word(ctx+0x5fd,&nf) ||
       !word(ctx+0x5f1,&second) || !word(ctx+0x5f5,&ns) ||
       !word(ctx+0x601,&mapping) || nf<1 || nf>256 ||
       ns<1 || ns>256 || !word(reg,&rows) || !word(reg+4,&nr) ||
       nr<1 || nr>16) return 0;
    if(!put(fd,"PCR5SP01",8)) return 0;
    for(unsigned i=0;i<sizeof globals/sizeof globals[0];++i)
        if(!range(fd,globals[i],4)) return 0;
    if(!range(fd,cb,clubs*581) || !range(fd,sb,staff*110) ||
       !range(fd,ctx,0x605) || !range(fd,mapping,(clubs+32)*0x91) ||
       !range(fd,first,nf*6371) || !range(fd,second,ns*6371) ||
       !range(fd,reg,8) || !range(fd,rows,nr*0xa6ef)) return 0;
    return put(fd,"PCR5DONE",8) && fsync(fd)==0;
}
void __real_f_005cde40(void);
void __wrap_f_005cde40(void)
{
    if(!seen) {
        seen=1;
        const char *path=getenv("PC_R5_CAPTURE");
        if(path && *path) {
            int saved=errno;
            Cpu before=cpu; Fpu fp_before=fpu;
            int fd=open(path,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);
            int ok=fd>=0 && capture(fd);
            if(fd>=0 && close(fd)) ok=0;
            if(memcmp(&before,&cpu,sizeof cpu) || memcmp(&fp_before,&fpu,sizeof fpu))
                _exit(92);
            fprintf(stderr,"pc-r5: first-human-turn capture %s\n",ok?"complete":"failed");
            errno=saved;
        }
    }
    __real_f_005cde40();
}
