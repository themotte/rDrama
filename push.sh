git pull
git add .
git commit -m "sneed"
git push

npm install -g sass
apt install ruby-sass
sass ./files/assets/css2/transparent.scss ./files/assets/css2/transparent_ff66ac.css
sass ./files/assets/css2/win98.scss ./files/assets/css2/win98_ff66ac.css
sass ./files/assets/css2/midnight.scss ./files/assets/css2/midnight_ff66ac.css
sass ./files/assets/css2/dark.scss ./files/assets/css2/dark_ff66ac.css
sass ./files/assets/css2/light.scss ./files/assets/css2/light_ff66ac.css
sass ./files/assets/css2/coffee.scss ./files/assets/css2/coffee_ff66ac.css
sass ./files/assets/css2/tron.scss ./files/assets/css2/tron_ff66ac.css
sass ./files/assets/css2/4chan.scss ./files/assets/css2/4chan_ff66ac.css
python ./compilecss.py
python3 ./compilecss.py
git add .
git commit -m "css"
git push

cd D:\1
git pull