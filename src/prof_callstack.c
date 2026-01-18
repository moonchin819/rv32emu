#include "prof_callstack.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { uint32_t addr; uint16_t idx; char name[64]; } sym_t;
static sym_t *syms = NULL; static size_t nsyms = 0;
static const char **idx2name = NULL; static size_t nidx = 0;

typedef struct { uint16_t *v; size_t len; size_t cap; } stack_t;
static stack_t stk; static uint64_t stk_cnt = 0;

typedef struct { uint16_t *v; size_t len; uint64_t cnt; } entry_t;
static entry_t *map = NULL; static size_t nmap = 0, cmap = 0;

static void stack_push(uint16_t x){ if(stk.len==stk.cap){stk.cap=stk.cap?stk.cap*2:8; stk.v=realloc(stk.v,stk.cap*sizeof(uint16_t));} stk.v[stk.len++]=x; }
static void stack_pop(void){ if(stk.len) stk.len--; }
static int cmp_sym(const void*a,const void*b){ return ((sym_t*)a)->addr > ((sym_t*)b)->addr ? 1 : -1; }
static uint16_t sym_of(uint32_t pc){
    // 二分搜尋：找到 sym[i].addr <= pc < sym[i+1].addr
    size_t l=0,r=nsyms; if(!nsyms) return 0;
    while(l+1<r){ size_t m=(l+r)/2; if(syms[m].addr<=pc) l=m; else r=m; }
    return syms[l].idx;
}
static void save_current(void){
    if(!stk.len) return;
    // 轉成 key；這裡用線性搜尋簡化（樣本小 OK），要快可用 hash
    for(size_t i=0;i<nmap;i++){
        if(map[i].len==stk.len && memcmp(map[i].v, stk.v, stk.len*sizeof(uint16_t))==0){
            map[i].cnt += stk_cnt; stk_cnt=0; return;
        }
    }
    if(nmap==cmap){ cmap = cmap?cmap*2:16; map = realloc(map, cmap*sizeof(entry_t)); }  // nmap = 16時，代表滿了
    map[nmap].v = malloc(stk.len*sizeof(uint16_t));
    memcpy(map[nmap].v, stk.v, stk.len*sizeof(uint16_t));
    map[nmap].len = stk.len;
    map[nmap].cnt = stk_cnt;
    stk_cnt = 0; nmap++;
}

void prof_init(const char *sym_path, uint32_t entry_pc){
    FILE *fp = fopen(sym_path, "r"); if(!fp) return;
    char line[256]; uint32_t addr; char type, name[128];
    while(fgets(line,sizeof(line),fp)){
        if(sscanf(line, "%x %c %127s", &addr, &type, name)!=3) continue;
        if(!(type=='T'||type=='t'||type=='W'||type=='w')) continue;
        syms = realloc(syms, (nsyms+1)*sizeof(sym_t));  // add one more slot
        syms[nsyms].addr = addr; 
        syms[nsyms].idx  = (uint16_t)(nsyms+1);  // start from 1
        strncpy(syms[nsyms].name, name, sizeof(syms[nsyms].name)-1);  // copy the name
        syms[nsyms].name[sizeof(syms[nsyms].name)-1]=0;
        nsyms++;
    }
    fclose(fp);
    qsort(syms, nsyms, sizeof(sym_t), cmp_sym);
    nidx = nsyms+1; idx2name = calloc(nidx, sizeof(char*));
    for(size_t i=0;i<nsyms;i++) 
        idx2name[syms[i].idx] = syms[i].name;
    // initialize stack：entry_pc is the first function
    uint16_t entry_idx = sym_of(entry_pc);
    if(entry_idx) stack_push(entry_idx);
    stk_cnt = 0;
}

void prof_on_jal(uint32_t target_pc, bool tail_call){
    save_current();
    if(tail_call && stk.len) stack_pop();
    uint16_t idx = sym_of(target_pc);
    if(idx) stack_push(idx);
}

void prof_on_jalr(uint32_t target_pc, bool is_ret, bool tail_call){
    save_current();
    if(is_ret && stk.len) stack_pop();
    else {
        if(tail_call && stk.len) stack_pop();
        uint16_t idx = sym_of(target_pc);
        if(idx) stack_push(idx);
    }
}
void prof_on_inst(void){ stk_cnt++; }

void prof_finish(const char *out_path){
    save_current();
    FILE *fp = fopen(out_path,"w"); if(!fp) return;
    for(size_t i=0;i<nmap;i++){
        if(map[i].cnt==0) continue;
        for(size_t j=0;j<map[i].len;j++){
            const char* nm = (map[i].v[j] < nidx)? idx2name[map[i].v[j]]:NULL;
            if(nm) fprintf(fp, "%s;", nm);
        }
        fprintf(fp, " %llu\n", (unsigned long long)map[i].cnt);
    }
    fclose(fp);
}