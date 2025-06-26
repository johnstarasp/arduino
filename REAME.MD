wget -P ~/Documents/ http://www.waveshare.net/w/upload/0/02/SIM7080G_Cat_M_NB_IoT_HAT_Code.7z
sudo apt-get install p7zip
cd ~/Documents
sudo p7zip --uncompress SIM7080G_Cat_M_NB_IoT_HAT_Demo_Code.7z
sh ~/Documents/SIM7080G_Cat_M_NB_IoT_HAT_Demo_Code/pi_gpio_init.sh
sudo pip install RPi.GPIO
sudo apt-get install python-serial

cd ~/Documents/SIM7080G_Cat_M_NB_IoT_HAT_Demo_Code/python/mqtt
sudo python mqtt.py