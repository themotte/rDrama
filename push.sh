git pull
git add .
git commit -m "sneed"
git push

apt install ruby-sass
sass ./drama/assets/style/midnight.scss ./drama/assets/style/midnight_ff66ac.css
sass ./drama/assets/style/dark.scss ./drama/assets/style/dark_ff66ac.css
sass ./drama/assets/style/light.scss ./drama/assets/style/light_ff66ac.css
sass ./drama/assets/style/coffee.scss ./drama/assets/style/coffee_ff66ac.css
sass ./drama/assets/style/tron.scss ./drama/assets/style/tron_ff66ac.css
sass ./drama/assets/style/4chan.scss ./drama/assets/style/4chan_ff66ac.css
python ./compilecss.py
python3 ./compilecss.py
git add .
git commit -m "css"
git push

cd D:\1
git pull