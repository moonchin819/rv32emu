#pragma once
#include <stdint.h>
#include <stdbool.h>

void prof_init(const char *sym_path, uint32_t entry_pc);
void prof_on_jal(uint32_t target_pc, bool tail_call);
void prof_on_jalr(uint32_t target_pc, bool is_ret, bool tail_call);
void prof_on_inst(void);                // 每條退休指令呼叫一次
void prof_finish(const char *out_path); // 結束時輸出