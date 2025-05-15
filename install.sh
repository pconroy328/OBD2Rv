sudo cp obd2.service /etc/systemd/system/.
sudo chmod 644 /etc/systemd/system/obd2.service
sudo systemctl daemon-reload
sudo systemctl start obd2
sudo systemctl status obd2
sudo systemctl enable obd2
