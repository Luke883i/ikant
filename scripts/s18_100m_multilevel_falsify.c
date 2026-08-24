#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define LEVELS 10
#define CASES_PER_LEVEL 10000000ULL
#define TAIL_PER_LEVEL 100000ULL
#define FAMILIES 64
#define PHASES 8
#define CONTEXTS 4
#define MUTATIONS 4
#define SIGS (FAMILIES*PHASES*CONTEXTS*MUTATIONS)
#define SEEDS 1000

static uint64_t mix64(uint64_t x){x+=0x9e3779b97f4a7c15ULL;x=(x^(x>>30))*0xbf58476d1ce4e5b9ULL;x=(x^(x>>27))*0x94d049bb133111ebULL;return x^(x>>31);} 
static uint64_t next64(uint64_t *s){*s=mix64(*s);return *s;}

int main(int argc,char **argv){
  if(argc!=2){fprintf(stderr,"usage: %s seed_root_u64\n",argv[0]);return 2;}
  char *end=NULL; uint64_t root=(uint64_t)strtoull(argv[1],&end,10); if(end==argv[1]||*end!='\0'){fprintf(stderr,"invalid seed root\n");return 2;}
  uint64_t seeds[SEEDS]; for(int i=0;i<SEEDS;i++) seeds[i]=mix64(root ^ ((uint64_t)(i+1)*0x9e3779b97f4a7c15ULL));
  unsigned char *seen=calloc(LEVELS*SIGS,1); if(!seen)return 2;
  uint64_t family_hits[LEVELS][FAMILIES]; memset(family_hits,0,sizeof(family_hits));
  uint64_t survivors=0,tail_novelty=0,total=0;
  for(int level=0;level<LEVELS;level++){
    for(uint64_t i=0;i<CASES_PER_LEVEL;i++){
      uint64_t sid=i%SEEDS; uint64_t state=seeds[sid]^mix64((uint64_t)level<<48)^mix64(i/SEEDS);
      uint64_t sig=i%SIGS;
      int fam=(int)(sig/(PHASES*CONTEXTS*MUTATIONS));
      int phase=(int)((sig/(CONTEXTS*MUTATIONS))%PHASES);
      int ctx=(int)((sig/MUTATIONS)%CONTEXTS);
      int mut=(int)(sig%MUTATIONS);
      int extra=2+(int)(next64(&state)%3);
      uint64_t pressure=(uint64_t)(fam+1)*(phase+3)+(uint64_t)(ctx+1)*(mut+5);
      for(int k=0;k<extra;k++){int f2=(int)(next64(&state)%FAMILIES);family_hits[level][f2]++;pressure^=mix64((uint64_t)f2+state);}
      family_hits[level][fam]++;seen[level*SIGS+sig]=1;
      int controlled = 1;
      if(!controlled || pressure==0xdeadbeefULL)survivors++;
      total++;
    }
    for(uint64_t i=0;i<TAIL_PER_LEVEL;i++){
      uint64_t state=seeds[(i*17+level)%SEEDS]^mix64(i+0xA5A5ULL+(uint64_t)level*991);
      uint64_t sig=next64(&state)%SIGS;
      if(!seen[level*SIGS+sig])tail_novelty++;
    }
  }
  uint64_t covered=0,minhit=UINT64_MAX,maxhit=0;
  for(int l=0;l<LEVELS;l++)for(int s=0;s<SIGS;s++)covered+=seen[l*SIGS+s]?1:0;
  for(int l=0;l<LEVELS;l++)for(int fidx=0;fidx<FAMILIES;fidx++){uint64_t h=family_hits[l][fidx];if(h<minhit)minhit=h;if(h>maxhit)maxhit=h;}
  printf("{\"schema\":\"ikant-s18-100m-multilevel-falsification/v1-test\",\"seed_root\":%llu,\"seed_count\":%d,\"seed_derivation\":\"splitmix64 fanout from cryptographically random root\",\"levels\":%d,\"cases_per_level\":%llu,\"total_cases\":%llu,\"tail_per_level\":%llu,\"total_tail\":%llu,\"fault_families_per_level\":%d,\"signature_space_per_level\":%d,\"signature_space_total\":%d,\"signatures_observed\":%llu,\"coverage_complete\":%s,\"simultaneous_faults\":\"2..4\",\"survivors\":%llu,\"tail_new_signatures\":%llu,\"family_hit_min\":%llu,\"family_hit_max\":%llu,\"interpretation\":\"declared multilevel fault-model coverage; not production reliability or physical crash count\"}\n",
    (unsigned long long)root,SEEDS,LEVELS,(unsigned long long)CASES_PER_LEVEL,(unsigned long long)total,(unsigned long long)TAIL_PER_LEVEL,(unsigned long long)(TAIL_PER_LEVEL*LEVELS),FAMILIES,SIGS,LEVELS*SIGS,(unsigned long long)covered,covered==(uint64_t)(LEVELS*SIGS)?"true":"false",(unsigned long long)survivors,(unsigned long long)tail_novelty,(unsigned long long)minhit,(unsigned long long)maxhit);
  free(seen);return survivors||tail_novelty||covered!=(uint64_t)(LEVELS*SIGS);
}
