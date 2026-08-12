from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
import sqlite3
from datetime import datetime

DB = "medical_shop.db"

KV = r"""
ScreenManager:
    LoginScreen:
    DashboardScreen:
    InventoryScreen:
    BillingScreen:
    SalesScreen:

<LoginScreen>:
    name: "login"
    BoxLayout:
        orientation: "vertical"
        padding: dp(30)
        spacing: dp(15)
        Label:
            text: "💊 MEDICAL SHOP"
            font_size: "28sp"
            bold: True
        TextInput:
            id: username
            hint_text: "Username"
            multiline: False
        TextInput:
            id: password
            hint_text: "Password"
            password: True
            multiline: False
        Button:
            text: "LOGIN"
            size_hint_y: None
            height: dp(50)
            on_release: root.login()
        Label:
            text: "Default: admin / admin123"

<DashboardScreen>:
    name: "dashboard"
    BoxLayout:
        orientation: "vertical"
        padding: dp(20)
        spacing: dp(12)
        Label:
            text: "Dashboard"
            font_size: "26sp"
            bold: True
        Label:
            id: summary
            text: ""
            font_size: "18sp"
        Button:
            text: "Inventory"
            on_release: app.root.current = "inventory"
        Button:
            text: "Billing"
            on_release: app.root.current = "billing"
        Button:
            text: "Sales History"
            on_release: app.root.current = "sales"
        Button:
            text: "Refresh"
            on_release: root.refresh()

<InventoryScreen>:
    name: "inventory"
    BoxLayout:
        orientation: "vertical"
        padding: dp(15)
        spacing: dp(8)
        Label:
            text: "Medicine Inventory"
            font_size: "24sp"
            bold: True
        TextInput:
            id: medname
            hint_text: "Medicine name"
            multiline: False
        TextInput:
            id: qty
            hint_text: "Quantity"
            input_filter: "int"
            multiline: False
        TextInput:
            id: price
            hint_text: "Selling price"
            input_filter: "float"
            multiline: False
        Button:
            text: "Add Medicine"
            on_release: root.add_medicine()
            size_hint_y: None
            height: dp(50)
        Label:
            id: list
            text: ""
            halign: "left"
            valign: "top"
        Button:
            text: "Back"
            on_release: app.root.current = "dashboard"

<BillingScreen>:
    name: "billing"
    BoxLayout:
        orientation: "vertical"
        padding: dp(15)
        spacing: dp(10)
        Label:
            text: "Billing"
            font_size: "24sp"
            bold: True
        TextInput:
            id: search
            hint_text: "Medicine name"
            multiline: False
        TextInput:
            id: bqty
            hint_text: "Quantity"
            input_filter: "int"
            multiline: False
        Button:
            text: "Create Bill"
            on_release: root.create_bill()
        Label:
            id: result
            text: ""
        Button:
            text: "Back"
            on_release: app.root.current = "dashboard"

<SalesScreen>:
    name: "sales"
    BoxLayout:
        orientation: "vertical"
        padding: dp(15)
        spacing: dp(8)
        Label:
            text: "Sales History"
            font_size: "24sp"
            bold: True
        Label:
            id: sales
            text: ""
            halign: "left"
            valign: "top"
        Button:
            text: "Refresh"
            on_release: root.refresh()
        Button:
            text: "Back"
            on_release: app.root.current = "dashboard"
"""

def db_init():
    con = sqlite3.connect(DB)
    c = con.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS medicines(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        quantity INTEGER DEFAULT 0,
        price REAL DEFAULT 0,
        purchase_price REAL DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS sales(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        medicine_id INTEGER,
        medicine_name TEXT,
        quantity INTEGER,
        total REAL,
        sale_date TEXT)""")
    con.commit()
    con.close()

class LoginScreen(Screen):
    def login(self):
        if self.ids.username.text == "admin" and self.ids.password.text == "admin123":
            self.manager.current = "dashboard"
            self.manager.get_screen("dashboard").refresh()
        else:
            self.ids.password.text = ""
            self.ids.username.text = ""

class DashboardScreen(Screen):
    def on_pre_enter(self):
        self.refresh()
    def refresh(self):
        con = sqlite3.connect(DB)
        c = con.cursor()
        c.execute("SELECT COUNT(*), COALESCE(SUM(quantity),0) FROM medicines")
        meds, stock = c.fetchone()
        c.execute("SELECT COALESCE(SUM(total),0) FROM sales WHERE date(sale_date)=date('now')")
        sales = c.fetchone()[0]
        con.close()
        self.ids.summary.text = f"Medicines: {meds}\nStock Units: {stock}\nToday's Sales: ₹{sales:.2f}"

class InventoryScreen(Screen):
    def on_pre_enter(self):
        self.refresh()
    def refresh(self):
        con = sqlite3.connect(DB)
        rows = con.execute("SELECT name,quantity,price FROM medicines ORDER BY name").fetchall()
        con.close()
        self.ids.list.text = "\n".join(f"{n} | Qty: {q} | ₹{p:.2f}" for n,q,p in rows) or "No medicines."
    def add_medicine(self):
        name = self.ids.medname.text.strip()
        try:
            qty = int(self.ids.qty.text)
            price = float(self.ids.price.text)
        except ValueError:
            return
        if not name or qty < 0 or price < 0:
            return
        con = sqlite3.connect(DB)
        con.execute("INSERT INTO medicines(name,quantity,price) VALUES(?,?,?)",(name,qty,price))
        con.commit()
        con.close()
        self.ids.medname.text = self.ids.qty.text = self.ids.price.text = ""
        self.refresh()

class BillingScreen(Screen):
    def create_bill(self):
        name = self.ids.search.text.strip()
        try:
            qty = int(self.ids.bqty.text)
        except ValueError:
            self.ids.result.text = "Invalid quantity"
            return
        con = sqlite3.connect(DB)
        row = con.execute("SELECT id,name,quantity,price FROM medicines WHERE name LIKE ? LIMIT 1",(name,)).fetchone()
        if not row:
            self.ids.result.text = "Medicine not found"
            con.close()
            return
        mid, mname, stock, price = row
        if qty <= 0 or qty > stock:
            self.ids.result.text = f"Available stock: {stock}"
            con.close()
            return
        total = qty * price
        con.execute("UPDATE medicines SET quantity=quantity-? WHERE id=?",(qty,mid))
        con.execute("INSERT INTO sales(medicine_id,medicine_name,quantity,total,sale_date) VALUES(?,?,?,?,?)",
                    (mid,mname,qty,total,datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        con.commit()
        con.close()
        self.ids.result.text = f"Bill created\n{mname} x {qty}\nTotal: ₹{total:.2f}"
        self.ids.search.text = self.ids.bqty.text = ""

class SalesScreen(Screen):
    def on_pre_enter(self):
        self.refresh()
    def refresh(self):
        con = sqlite3.connect(DB)
        rows = con.execute("SELECT medicine_name,quantity,total,sale_date FROM sales ORDER BY id DESC").fetchall()
        con.close()
        self.ids.sales.text = "\n".join(
            f"{n} | Qty: {q} | ₹{t:.2f} | {d}" for n,q,t,d in rows
        ) or "No sales yet."

class MedicalShopApp(App):
    def build(self):
        db_init()
        return Builder.load_string(KV)

if __name__ == "__main__":
    MedicalShopApp().run()
