git pull
git add .
git commit -m "sneed"
git push

sass ./ruqqus/assets/style/dark.scss D:/#D/ruqqus/assets/style/dark_ff66ac.css
sass ./ruqqus/assets/style/light.scss D:/#D/ruqqus/assets/style/light_ff66ac.css
sass ./ruqqus/assets/style/coffee.scss D:/#D/ruqqus/assets/style/coffee_ff66ac.css
sass ./ruqqus/assets/style/tron.scss D:/#D/ruqqus/assets/style/tron_ff66ac.css
sass ./ruqqus/assets/style/4chan.scss D:/#D/ruqqus/assets/style/4chan_ff66ac.css
python ./compilecss.py
git add .
git commit -m "css"
git push

cd D:\1
git pull