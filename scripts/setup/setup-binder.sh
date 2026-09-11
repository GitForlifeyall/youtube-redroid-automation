#!/bin/bash
set -e

mkdir -p /dev/binderfs
mount -t binder binder /dev/binderfs 2>/dev/null || true
ln -sf /dev/binderfs/binder /dev/binder 2>/dev/null || true
ln -sf /dev/binderfs/hwbinder /dev/hwbinder 2>/dev/null || true
ln -sf /dev/binderfs/vndbinder /dev/vndbinder 2>/dev/null || true
chmod 777 /dev/binderfs/* /dev/binder* 2>/dev/null || true

cat << 'EOF' > /etc/wsl.conf
[boot]
systemd=true
command="mkdir -p /dev/binderfs && mount -t binder binder /dev/binderfs 2>/dev/null; ln -sf /dev/binderfs/binder /dev/binder 2>/dev/null; ln -sf /dev/binderfs/hwbinder /dev/hwbinder 2>/dev/null; ln -sf /dev/binderfs/vndbinder /dev/vndbinder 2>/dev/null; chmod 777 /dev/binderfs/* /dev/binder* 2>/dev/null"
EOF

echo "Binder configured successfully"
