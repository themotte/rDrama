for f in *.webp; do 
    convert "$f" -layers coalesce -resize 200x "$f"
done