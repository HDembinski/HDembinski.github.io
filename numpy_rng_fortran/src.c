#include "pcg64/pcg64.h"
#include <stdio.h>

extern void set_rstate(void**);

pcg64_random_t static_rstate;

// never called from Fortran
static inline double uint64_to_double(uint64_t rnd){
    return (rnd >> 11) * (1.0 / 9007199254740992.0);
}

// this is called from Fortran
void next_(double* value, void** rstate)
{
    uint64_t r = pcg64_random_r((pcg64_random_t*)*rstate);
    *value = uint64_to_double(r);
}

void init_() {
    // This is a just dummy implementation.
    // We would create/initialize the RNG in Python,
    // and then pass the opaque pointer to its state
    // to Fortran, where the pointer is stored in a
    // common block
    pcg_cm_srandom_r(&static_rstate, 1, 1);
    void* ptr = &static_rstate;
    set_rstate(&ptr);
}