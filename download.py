import urllib.request
import os

url = "https://raw.githubusercontent.com/juliankic/GHL-AdId/main/app.py"
path = r"C:\xtrategy-adid\app.py"

if os.path.exists(path):
    os.remove(path)

req = urllib.request.Request(url, headers={"Cache-Control": "no-cache", "Pragma": "no-cache"})
data = urllib.request.urlopen(req).read()

with open(path, "wb") as f:
    f.write(data)

print("Bytes escritos: " + str(len(data)))
print("Linea 174-177:")
lines = data.decode("utf-8").splitlines()
for i, line in enumerate(lines[173:177], start=174):
    print(str(i) + ": " + line)
