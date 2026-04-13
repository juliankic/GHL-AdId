import urllib.request
import os
url = "https://raw.githubusercontent.com/juliankic/GHL-AdId/main/app.py"
urllib.request.urlretrieve(url, r"C:\xtrategy-adid\app.py")
print("Descargado OK")
print("Tamanio:", os.path.getsize(r"C:\xtrategy-adid\app.py"), "bytes")
