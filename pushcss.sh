cd D:\1
git pull

sass ./drama/assets/style/dark.scss D:/#D/drama/assets/style/dark_ff66ac.css
sass ./drama/assets/style/light.scss D:/#D/drama/assets/style/light_ff66ac.css
sass ./drama/assets/style/coffee.scss D:/#D/drama/assets/style/coffee_ff66ac.css
sass ./drama/assets/style/tron.scss D:/#D/drama/assets/style/tron_ff66ac.css
sass ./drama/assets/style/4chan.scss D:/#D/drama/assets/style/4chan_ff66ac.css
python ./compilecss.py
git add .
git commit -m "css"
git push