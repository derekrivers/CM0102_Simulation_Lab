#define _GNU_SOURCE
#define _LARGEFILE64_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <unistd.h>

/* Original host observer, no upstream implementation copied. Private metadata
 * only: never log file contents. Every event inspects its actual live fd. */
static int trace_fd = -1;
static uint64_t sequence, trace_bytes, dropped, errors;
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static __thread int logging;
#define CAP (16u * 1024u * 1024u)
#define DECL(ret, name, args) static ret (*real_##name) args
DECL(int, open, (const char *, int, ...));
DECL(int, open64, (const char *, int, ...));
DECL(int, openat, (int, const char *, int, ...));
DECL(int, openat64, (int, const char *, int, ...));
DECL(FILE *, fopen, (const char *, const char *));
DECL(FILE *, fopen64, (const char *, const char *));
DECL(ssize_t, read, (int, void *, size_t));
DECL(ssize_t, pread, (int, void *, size_t, off_t));
DECL(ssize_t, pread64, (int, void *, size_t, off64_t));
DECL(size_t, fread, (void *, size_t, size_t, FILE *));
DECL(size_t, fread_unlocked, (void *, size_t, size_t, FILE *));
DECL(void *, mmap, (void *, size_t, int, int, int, off_t));
DECL(void *, mmap64, (void *, size_t, int, int, int, off64_t));
#define RESOLVE(n) do { if (!real_##n) *(void **)(&real_##n) = dlsym(RTLD_NEXT, #n); if (!real_##n) _exit(125); } while (0)

static void hexpath(char *out, size_t cap, const char *path) {
    static const char h[] = "0123456789abcdef";
    size_t i = 0;
    if (path) for (; path[i] && i * 2 + 2 < cap; ++i) {
        unsigned char c = (unsigned char)path[i];
        out[i*2] = h[c >> 4]; out[i*2+1] = h[c & 15];
    }
    out[i*2] = 0;
}
static void emit(const char *op, int fd, int success, int64_t result,
                 uint64_t requested, int saved_errno, const char *supplied) {
    int entry_errno = errno;
    if (logging || trace_fd < 0) return;
    logging = 1;
    char target[4096] = "", locator[64], target_hex[8192], supplied_hex[8192];
    struct stat st = {0};
    int identity_ok = 0;
    if (fd >= 0) {
        snprintf(locator, sizeof locator, "/proc/self/fd/%d", fd);
        ssize_t count = syscall(SYS_readlink, locator, target, sizeof target-1);
        if (count >= 0 && count < (ssize_t)sizeof target-1 &&
            syscall(SYS_fstat, fd, &st) == 0) {
            target[count] = 0;
            identity_ok = 1;
        }
    }
    hexpath(target_hex, sizeof target_hex, target);
    hexpath(supplied_hex, sizeof supplied_hex, supplied);
    pthread_mutex_lock(&lock);
    char line[18000];
    int len = snprintf(line, sizeof line,
        "%" PRIu64 "\t%s\t%d\t%" PRId64 "\t%" PRIu64 "\t%d\t%d\t%" PRIu64 "\t%" PRIu64 "\t%" PRId64 "\t%s\t%s\n",
        ++sequence, op, success, result, requested, success ? 0 : saved_errno,
        identity_ok, (uint64_t)st.st_dev, (uint64_t)st.st_ino,
        (int64_t)st.st_size, target_hex, supplied_hex);
    if (len < 0 || len >= (int)sizeof line || trace_bytes + (unsigned)len > CAP-256) {
        ++dropped;
    } else {
        ssize_t wrote = syscall(SYS_write, trace_fd, line, (size_t)len);
        if (wrote != len) ++errors;
        else trace_bytes += (unsigned)len;
    }
    pthread_mutex_unlock(&lock);
    logging = 0;
    errno = entry_errno;
}
__attribute__((constructor)) static void begin(void) {
    const char *path = getenv("PC_R9_TRACE");
    if (!path) return;
    trace_fd = (int)syscall(SYS_openat, AT_FDCWD, path,
                           O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC|O_NOFOLLOW, 0600);
    if (trace_fd < 0) _exit(124);
    const char header[] = "PCR9FILE1\n";
    if (syscall(SYS_write, trace_fd, header, sizeof header-1) != sizeof header-1)
        _exit(123);
    trace_bytes = sizeof header-1;
}
__attribute__((destructor)) static void finish(void) {
    if (trace_fd < 0) return;
    pthread_mutex_lock(&lock);
    char line[160];
    int len = snprintf(line, sizeof line, "PCR9DONE\t%" PRIu64 "\t%" PRIu64 "\t%" PRIu64 "\n",
                       sequence, dropped, errors);
    if (syscall(SYS_write, trace_fd, line, (size_t)len) != len) _exit(122);
    if (syscall(SYS_fsync, trace_fd) != 0) _exit(121);
    syscall(SYS_close, trace_fd);
    trace_fd = -1;
    pthread_mutex_unlock(&lock);
}
static int needs_mode(int flags) {
    return (flags & O_CREAT) || ((flags & O_TMPFILE) == O_TMPFILE);
}
#define OPEN_WRAP(n) \
int n(const char *path, int flags, ...) { \
    RESOLVE(n); mode_t mode = 0; \
    if (needs_mode(flags)) { va_list ap; va_start(ap, flags); mode = va_arg(ap, mode_t); va_end(ap); } \
    int fd = real_##n(path, flags, mode); int e = errno; \
    emit(#n, fd, fd >= 0, fd >= 0 ? 0 : -1, (unsigned)flags, e, path); errno = e; return fd; \
}
OPEN_WRAP(open)
OPEN_WRAP(open64)
#define OPENAT_WRAP(n) \
int n(int dir, const char *path, int flags, ...) { \
    RESOLVE(n); mode_t mode = 0; \
    if (needs_mode(flags)) { va_list ap; va_start(ap, flags); mode = va_arg(ap, mode_t); va_end(ap); } \
    int fd = real_##n(dir, path, flags, mode); int e = errno; \
    emit(#n, fd, fd >= 0, fd >= 0 ? 0 : -1, (unsigned)flags, e, path); errno = e; return fd; \
}
OPENAT_WRAP(openat)
OPENAT_WRAP(openat64)
#define FOPEN_WRAP(n) \
FILE *n(const char *path, const char *mode) { \
    RESOLVE(n); FILE *f = real_##n(path, mode); int e = errno; \
    emit(#n, f ? fileno(f) : -1, f != NULL, f ? 0 : -1, 0, e, path); errno = e; return f; \
}
FOPEN_WRAP(fopen)
FOPEN_WRAP(fopen64)
ssize_t read(int fd, void *buf, size_t count) {
    RESOLVE(read); ssize_t r = real_read(fd, buf, count); int e = errno;
    emit("read", fd, r >= 0, r, count, e, NULL); errno = e; return r;
}
#define PREAD_WRAP(n,t) \
ssize_t n(int fd, void *buf, size_t count, t offset) { \
    RESOLVE(n); ssize_t r = real_##n(fd, buf, count, offset); int e = errno; \
    emit(#n, fd, r >= 0, r, count, e, NULL); errno = e; return r; \
}
PREAD_WRAP(pread, off_t)
PREAD_WRAP(pread64, off64_t)
#define FREAD_WRAP(n) \
size_t n(void *buf, size_t size, size_t count, FILE *f) { \
    RESOLVE(n); size_t r = real_##n(buf, size, count, f); int e = errno; \
    uint64_t asked = size && count > UINT64_MAX / size ? UINT64_MAX : (uint64_t)size * count; \
    uint64_t got = (uint64_t)r * size; \
    emit(#n, fileno(f), !ferror(f), (int64_t)got, asked, e, NULL); errno = e; return r; \
}
FREAD_WRAP(fread)
FREAD_WRAP(fread_unlocked)
#define MMAP_WRAP(n,t) \
void *n(void *addr, size_t len, int prot, int flags, int fd, t offset) { \
    RESOLVE(n); void *r = real_##n(addr, len, prot, flags, fd, offset); int e = errno; \
    emit(#n, fd, r != MAP_FAILED, r != MAP_FAILED ? 0 : -1, len, e, NULL); errno = e; return r; \
}
MMAP_WRAP(mmap, off_t)
MMAP_WRAP(mmap64, off64_t)
