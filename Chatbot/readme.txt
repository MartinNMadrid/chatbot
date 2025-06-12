#EL CHATBOT NECESITA
#FUZZYWUZZY - VENV - FLASK - WSGI

Guardar en /var/www/html/chatbot
Mover /SITES-AVAILABLE/moodle.conf a /etc/apache2/sites-available/
Crear entorno virtual venv en /chatbot

--PROCEDIMIENTO

#Instalar WSGI
sudo apt install libapache2-mod-wsgi-py3
sudo a2enmod wsgi
sudo systemmctl restart apache2

#Permisos a chatbot
sudo chown -R www-data:www-data /var/www/html/chatbot/
sudo chmod -R 755 /var/www/html/chatbot/

#Crear entorno virtual
sudo apt install python3-venv -y
sudo chown -R $USER:$USER /var/www/html/chatbot
cd /var/www/html/chatbot
python3 -m venv venv
source venv/bin/activate
pip install flask fuzzywuzzy

sudo chown -R www-data:www-data /var/www/html/chatbot

#Ver errores
sudo tail -f /var/log/apache2/error.log