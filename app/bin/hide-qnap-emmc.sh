#!/bin/bash
# Hide only the known QNAP eMMC partitions when fnOS mounts them as removable storage.
LOG_FILE="${TRIM_PKGVAR:-/var/apps/qnap-emmc-hide/var}/hide-qnap-emmc.log"
INTERVAL=15
PARTITIONS=(1 2 3 5 6 7)
mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true
log_msg() { printf '[%s] %s\n' "$(date '+%F %T')" "$*" >> "$LOG_FILE"; }
unmount_emmc() {
  local n dev targets target result
  for n in "${PARTITIONS[@]}"; do
    dev="/dev/mmcblk0p${n}"
    targets="$(findmnt -rn -S "$dev" -o TARGET 2>/dev/null || true)"
    [ -n "$targets" ] || continue
    while IFS= read -r target; do
      [ -n "$target" ] || continue
      case "$target" in
        /vol00/RemovableDisk|/vol00/RemovableDisk_[0-9]*)
          if result=$(umount "$target" 2>&1); then
            log_msg "已卸载 $dev -> $target"
          else
            log_msg "卸载失败 $dev -> $target: ${result:-未知错误}"
          fi
          ;;
        *) log_msg "跳过 $dev 的非目标挂载点：$target" ;;
      esac
    done <<< "$targets"
  done
}
case "${1:-once}" in
  --daemon)
    log_msg "服务已启动；仅处理指定 eMMC 分区在 /vol00/RemovableDisk* 下的挂载"
    while :; do unmount_emmc; sleep "$INTERVAL"; done
    ;;
  once|--once) unmount_emmc ;;
  *) echo "Usage: $0 {--daemon|once}" >&2; exit 2 ;;
esac
