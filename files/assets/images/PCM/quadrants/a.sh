for f in *.gif; do
    convert "$f" -trim "$f"
done