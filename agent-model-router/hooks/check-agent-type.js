#!/usr/bin/env node
/**
 * PreToolUse / SessionStart hook。
 * PreToolUse 拦截 Agent 工具调用：
 * 1. 禁止 Explore 类型（没有 AskUserQuestion，弹框不出现）。
 * 2. 禁止 router-* 类型——如果本会话刚通过 setup/create-agent 生成了新定义，
 *    这些定义还未被 ZCode 加载，强行调用会报 Agent type not found。
 *    hook 通过检查标志文件判断（router.py 生成定义时写入）。
 * SessionStart（--session-start）：新会话启动时定义已加载，清除标志文件。
 *
 * ZCode Hook 协议：
 * - exit 0 = 放行；exit 2 = 阻止（deny），原因写 stderr。
 * - 每次调用追加日志到 %TEMP%/agent-model-router-hook.log。
 */
const fs = require('fs');
const os = require('os');
const path = require('path');

const LOG_FILE = path.join(os.tmpdir(), 'agent-model-router-hook.log');
const FLAG_FILE = path.join(os.tmpdir(), 'agent-model-router-new-defs.flag');

function log(obj) {
  try {
    fs.appendFileSync(LOG_FILE, JSON.stringify(Object.assign({ ts: new Date().toISOString() }, obj)) + '\n');
  } catch (e) { /* 日志失败不影响 hook 判定 */ }
}

let input = '';
process.stdin.on('data', (chunk) => { input += chunk; });
process.stdin.on('end', () => {
  // SessionStart 模式：新会话启动 = 定义已被 ZCode 加载，清除"刚生成未加载"标志
  if (process.argv[2] === '--session-start') {
    try {
      if (fs.existsSync(FLAG_FILE)) {
        fs.unlinkSync(FLAG_FILE);
        log({ event: 'session-start', flagCleared: true });
      }
    } catch (e) { log({ event: 'session-start', error: String(e) }); }
    process.exit(0);
  }
  try {
    const data = JSON.parse(input);
    const toolName = data.tool_name || data.toolName || '';
    const params = data.tool_input || data.parameters || data.params || data.input || {};
    const subagentType = params.subagent_type || params.subagentType || '';

    log({ toolName, subagentType });

    // 1. 拦截 Explore
    if (toolName === 'Agent' && subagentType === 'Explore') {
      process.stderr.write('禁止使用 Explore 类型子智能体。Explore 没有 AskUserQuestion 工具，插件弹框不会出现。请停止本次调用，按 agent-model-router 技能的流程改用 router-* 类型（尚未生成定义时先执行 /router-setup 并新建会话）。\n');
      process.exit(2);
    }

    // 2. 拦截 router-*（新定义未加载时）
    if (toolName === 'Agent' && subagentType.startsWith('router-')) {
      if (fs.existsSync(FLAG_FILE)) {
        process.stderr.write(
          `禁止使用 ${subagentType} 类型子智能体。当前会话刚通过 create-agent 生成了新定义，` +
          `ZCode 尚未加载。请停止启动，告知用户新建会话后重新执行。\n`
        );
        process.exit(2);
      }
    }

    // 其他情况：exit 0 放行
    process.exit(0);
  } catch (e) {
    log({ parseError: String(e), raw: input.slice(0, 500) });
    process.exit(0);
  }
});
