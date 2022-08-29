
# Install the canapy-rtc python package first


install: larkNames larkDaemon network enable start

reinstall: uninstall larkNames larkDaemon enable start

uninstall: stop disable
	sudo rm /etc/systemd/system/larkDaemon.service
	sudo rm /etc/systemd/system/larkNames.service

start:
	sudo systemctl start larkNames
	sudo systemctl start larkDaemon

stop:
	sudo systemctl stop larkNames
	sudo systemctl stop larkDaemon

enable:
	sudo systemctl enable larkNames
	sudo systemctl enable larkDaemon

disable:
	sudo systemctl disable larkNames
	sudo systemctl disable larkDaemon

.PHONY: larkNames
larkNames:
	sudo cp larkNames.service /etc/systemd/system/
	sudo chown root:root /etc/systemd/system/larkNames.service
	sudo chmod 644 /etc/systemd/system/larkNames.service

.PHONY: network
network:
	which firewall-cmd && sudo firewall-cmd --add-port=18500-19000/udp --add-port=18500-19000/tcp --permanent || echo "No firewall-cmd"
	which firewall-cmd && sudo firewall-cmd --reload || echo "No firewall-cmd"

.PHONY: larkDaemon
larkDaemon:
	sudo cp larkDaemon.service /etc/systemd/system/
	sudo chown root:root /etc/systemd/system/larkDaemon.service
	sudo chmod 644 /etc/systemd/system/larkDaemon.service