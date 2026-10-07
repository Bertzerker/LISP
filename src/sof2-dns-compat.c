/* Legacy Intel-compiled SoF2 uses a four-byte aligned i386 stack.
 * Realign its DNS entry point before calling modern NSS libraries.
 * Loaded only in SoF2 children; does not modify the system resolver. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <netdb.h>
__attribute__((force_align_arg_pointer))
struct hostent *gethostbyname(const char *name) {
    struct hostent *(*real_function)(const char *) = dlsym(RTLD_NEXT, "gethostbyname");
    if (!real_function) { h_errno = NO_RECOVERY; return 0; }
    return real_function(name);
}
