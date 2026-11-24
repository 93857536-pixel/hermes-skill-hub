#!/usr/bin/env bash
# pmset-probe.sh — 构建合盖保活类工具前的一次性环境探测
# 用法: bash pmset-probe.sh [hermes_home]  (默认 ~/.hermes)
set -u
HK="${1:-$HOME/.hermes}"

echo "=== 1) 当前 SleepDisabled flag ==="
pmset -g | grep -i SleepDisabled || echo "(无输出 = 0/默认)"

echo "=== 2) 合盖状态 ==="
ioreg -rc AppleClamshellState 2>/dev/null | grep -A1 AppleClamshellState || ioreg -rc IOService 2>/dev/null | grep -i Clamshell | head -3

echo "=== 3) sudo pmset 免密可用性(10s 超时,不挂起) ==="
if sudo -n pmset -g 2>/dev/null >/dev/null; then
  echo "OK: sudo -n pmset 可免密执行"
else
  echo "WARN: 需要密码或无权限 → 完整功能需 /etc/sudoers.d 加 NOPASSWD: /usr/bin/pmset"
fi

echo "=== 4) hermes 忙闲信号 ==="
DB="$HK/state.db"
if [ -f "$DB" ]; then
  AGE=$(( $(date +%s) - $(stat -f %m "$DB") ))
  echo "state.db 距今 ${AGE}s (默认 <120s 判 busy)"
else
  echo "state.db 不存在: $DB"
fi
GS="$HK/gateway_state.json"
if [ -f "$GS" ]; then
  python3 -c "
import json,os,sys
d=json.load(open('$GS'))
pid=d.get('pid')
alive=False
if pid:
    try: os.kill(int(pid),0); alive=True
    except Exception: pass
print('gateway pid=%s alive=%s active_agents=%s' % (pid, alive, d.get('active_agents')))
"
else
  echo "gateway_state.json 不存在: $GS"
fi

echo "=== 5) 电源 ==="
pmset -g batt | head -3
