
Remove (or make backup) sudo mv /home/pi/Desktop/App /home/pi/Desktop/App_bk

Copy App directory from source machine to /home/pi/Desktop/App /home/pi/Desktop/

Edit and run the chang_static_ip.sh script from /home/pi/Desktop/App /home/pi/Desktop/deployment/
Change the following line

NEW_IP_SUFFIX=15 #the IP suffix
NEW_CAM_IP_SUFFIX=5 # the camera ip suffix
NEW_BASE_IP=10.61.212. # the base ip

according to the configuration file of the site

Run deploy.sh (or deploy_qk7.sh for QK7 setup) will enable all services at startup

Check if all services work well. Then reboot to check startup script.

All change on .service file must call the ./deploy.sh to be activated

==================================
cd /home/pi/Desktop/App/deployment

# For GVM and Crown
./deploy.sh

# For QK7 run
./deploy_qk7.sh

.... wait, verify ...

sudo reboot

==================================


To start all services run

/home/pi/Desktop/App/deployment/start_all_services.sh


To restart all services run

/home/pi/Desktop/App/deployment/restart_all_services.sh


To stop all services run

/home/pi/Desktop/App/deployment/stop_all_services.sh


To disable all services on startup

/home/pi/Desktop/App/deployment/disable_services_on_boot.sh


To enable all services on startup

/home/pi/Desktop/App/deployment/enable_services_on_boot.sh

