## Branch 3.4.0

-install schema

-add WorkingDirectory in vw-gateway and Chang ExecStart in service

for example

Change according to the address of the Python file
```
cat << 'EOF' > vw-gateway.service
[Unit]
Description=My test service
After=multi-user.target
[Service]
Type=simple
Restart=always
WorkingDirectory=/root/.vw-gateway
ExecStart=/usr/bin/python3 "/root/git/odoo-iot/vw-gateway/main.py" --extension "/root/git/odoo-iot/vw-gateway/extensions"  --config "/root/.vw-gateway/conf.yaml"
[Install]
WantedBy=multi-user.target
EOF
```

-systemctl daemon-reload

-systemctl restart vw-gateway 

-Create logs Folder in WorkingDirectory

-Create logs.conf file

