#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define LEVELS 10
#define FAMILIES 32
#define PHASES 8
#define CONTEXTS 4
#define CLASSES 4
#define SIGS (FAMILIES*PHASES*CONTEXTS*CLASSES)
#define CASES 10000000ULL
#define TAIL 100000ULL

typedef struct { const char *name; const char *key; uint32_t residual_mask; } Level;

static uint64_t splitmix64(uint64_t *x){
  uint64_t z=(*x += 0x9e3779b97f4a7c15ULL);
  z=(z^(z>>30))*0xbf58476d1ce4e5b9ULL;
  z=(z^(z>>27))*0x94d049bb133111ebULL;
  return z^(z>>31);
}

static const Level levels[LEVELS] = {
 {"L0 Hardware / filesystem / power","hardware",0xF00000F3u},
 {"L1 Supply chain / model runtime","supply",0x0F000F0Fu},
 {"L2 Process / session / recovery","recovery",0x00F0F0F0u},
 {"L3 Admission / identity / authority","authority",0x000F000Fu},
 {"L4 Epistemic graph / provenance / memory","epistemic",0x0F0F00F0u},
 {"L5 Cognitive dynamics / psyche / oracle","cognitive",0x00FF0F00u},
 {"L6 Practical reason / planning / action","planning",0x0FF000F0u},
 {"L7 Temporal / hybrid / connectors / tools","external",0xF00FF000u},
 {"L8 Surface contract / PWA / UI state","surface",0x00F00FFFu},
 {"L9 Human UX / accessibility / trust","ux",0xF0F0F00Fu}
};

static int popcount32(uint32_t x){ int c=0; while(x){ x &= x-1; c++; } return c; }

int main(void){
  unsigned long long total_cases=0,total_survivors=0,total_tail_new=0;
  unsigned long long pair_hits[LEVELS][LEVELS]; memset(pair_hits,0,sizeof(pair_hits));
  printf("{\"schema\":\"ikant-100m-multilevel-falsification/v1-test\",\"cases_per_level\":%llu,\"tail_per_level\":%llu,\"levels\":[",(unsigned long long)CASES,(unsigned long long)TAIL);
  for(int l=0;l<LEVELS;l++){
    unsigned char *seen=(unsigned char*)calloc(SIGS,1); if(!seen) return 2;
    unsigned long long family_hits[FAMILIES]; memset(family_hits,0,sizeof(family_hits));
    unsigned long long survivors_by_family[FAMILIES]; memset(survivors_by_family,0,sizeof(survivors_by_family));
    unsigned long long survivors=0; int seen_count=0;
    uint64_t state=0x202608241349ULL ^ ((uint64_t)l*0xA5A5A5A5A5A5A5A5ULL);
    for(unsigned long long i=0;i<CASES;i++){
      uint64_t a=splitmix64(&state),b=splitmix64(&state),c=splitmix64(&state),d=splitmix64(&state),e=splitmix64(&state);
      int fam=(int)(a%FAMILIES),ph=(int)(b%PHASES),ctx=(int)(c%CONTEXTS),cls=(int)(d%CLASSES);
      int sig=(((fam*PHASES)+ph)*CONTEXTS+ctx)*CLASSES+cls;
      if(!seen[sig]){ seen[sig]=1; seen_count++; }
      family_hits[fam]++;
      int peer=(int)(e%LEVELS); pair_hits[l][peer]++;
      if((levels[l].residual_mask & (1u<<fam)) && (((ph+ctx+cls+(int)(e&3))%5)!=0)){
        survivors++; survivors_by_family[fam]++;
      }
    }
    unsigned long long min_hits=~0ULL,max_hits=0;
    for(int f=0;f<FAMILIES;f++){ if(family_hits[f]<min_hits)min_hits=family_hits[f]; if(family_hits[f]>max_hits)max_hits=family_hits[f]; }
    int before=seen_count; uint64_t tail_state=state ^ 0xDEADBEEF12345678ULL;
    for(unsigned long long i=0;i<TAIL;i++){
      int fam=(int)(splitmix64(&tail_state)%FAMILIES),ph=(int)(splitmix64(&tail_state)%PHASES),ctx=(int)(splitmix64(&tail_state)%CONTEXTS),cls=(int)(splitmix64(&tail_state)%CLASSES);
      int sig=(((fam*PHASES)+ph)*CONTEXTS+ctx)*CLASSES+cls;
      if(!seen[sig]){ seen[sig]=1; seen_count++; }
    }
    int tail_new=seen_count-before;
    if(l) printf(",");
    printf("{\"level\":%d,\"name\":\"%s\",\"key\":\"%s\",\"cases\":%llu,\"signature_space\":%d,\"signatures_observed\":%d,\"coverage_complete\":%s,\"family_min_hits\":%llu,\"family_max_hits\":%llu,\"modeled_residual_families\":%d,\"modeled_survivors\":%llu,\"survivor_rate\":%.9f,\"tail\":%llu,\"tail_new_signatures\":%d,\"top_residual_families\":[",l,levels[l].name,levels[l].key,(unsigned long long)CASES,SIGS,seen_count,seen_count==SIGS?"true":"false",min_hits,max_hits,popcount32(levels[l].residual_mask),survivors,(double)survivors/(double)CASES,(unsigned long long)TAIL,tail_new);
    int chosen[FAMILIES]; memset(chosen,0,sizeof(chosen)); int emitted=0;
    for(int rank=0;rank<5;rank++){
      int best=-1; unsigned long long bestv=0;
      for(int f=0;f<FAMILIES;f++) if(!chosen[f] && survivors_by_family[f]>bestv){ bestv=survivors_by_family[f]; best=f; }
      if(best<0 || bestv==0) break;
      if(emitted++) printf(",");
      printf("{\"family\":%d,\"survivors\":%llu}",best,bestv); chosen[best]=1;
    }
    printf("]}");
    total_cases += CASES; total_survivors += survivors; total_tail_new += (unsigned long long)tail_new;
    free(seen);
  }
  int pair_complete=1; for(int i=0;i<LEVELS;i++) for(int j=0;j<LEVELS;j++) if(pair_hits[i][j]==0) pair_complete=0;
  printf("],\"total_cases\":%llu,\"total_tail\":%llu,\"total_modeled_survivors\":%llu,\"cross_level_pair_matrix_complete\":%s,\"tail_new_signatures_total\":%llu,\"interpretation\":\"Modeled fault/precondition coverage over declared abstraction vocabularies; survivor counts rank known open control gaps and are not production failure probabilities, browser/OS executions, or formal verification.\"}\n",total_cases,(unsigned long long)(LEVELS*TAIL),total_survivors,pair_complete?"true":"false",total_tail_new);
  return 0;
}
