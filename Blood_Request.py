import mysql.connector
import qrcode
from datetime import datetime
import os
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import tkinter.ttk as ttk

# Valid blood groups and their compatibility
VALID_BLOOD_GROUPS = {'A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-'}
BLOOD_COMPATIBILITY = {
    'A+': ['A+', 'A-', 'O+', 'O-'],
    'A-': ['A-', 'O-'],
    'B+': ['B+', 'B-', 'O+', 'O-'],
    'B-': ['B-', 'O-'],
    'AB+': ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'],
    'AB-': ['A-', 'B-', 'AB-', 'O-'],
    'O+': ['O+', 'O-'],
    'O-': ['O-']
}

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'blood'
}

class QRCodeGenerator:
    @staticmethod
    def generate(data, donor_name, output_dir=""):
        try:
            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill='black', back_color='white')

            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)

            filename = f"{donor_name.replace(' ', '_')}_qr.png"
            filepath = os.path.join(output_dir, filename) if output_dir else filename
            img.save(filepath)
            print(f"✅ QR Code generated and saved at: {filepath}")

            QRCodeGenerator.show_qr_popup(filepath)
            return True
        except Exception as e:
            print(f"❌ Error generating QR code: {e}")
            return False

    @staticmethod
    def show_qr_popup(image_path):
        try:
            popup = tk.Toplevel()
            popup.title("Generated QR Code")

            img = Image.open(image_path)
            photo = ImageTk.PhotoImage(img)
            
            label = tk.Label(popup, image=photo)
            label.image = photo
            label.pack()

            close_btn = ttk.Button(popup, text="Close", command=popup.destroy)
            close_btn.pack(pady=10)

            popup.update_idletasks()
            width = popup.winfo_width()
            height = popup.winfo_height()
            x = (popup.winfo_screenwidth() // 2) - (width // 2)
            y = (popup.winfo_screenheight() // 2) - (height // 2)
            popup.geometry(f'+{x}+{y}')
        except Exception as e:
            print(f"❌ Error displaying QR code image: {e}")


def setup_database():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS units2 (
                blood_id INT AUTO_INCREMENT PRIMARY KEY,
                blood_type VARCHAR(5),
                quantity_ml INT,
                donor_id INT,
                donation_date DATE,
                expiration_date DATE,
                status VARCHAR(20) DEFAULT 'active'
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blood_requests (
                id INT AUTO_INCREMENT PRIMARY KEY,
                blood_type VARCHAR(5),
                request_date DATE,
                location VARCHAR(100),
                hospital_name VARCHAR(150),
                contact_number VARCHAR(15),
                status VARCHAR(20) DEFAULT 'pending',
                units_requested INT
            );
        """)

        connection.commit()
        print("✅ Database setup complete")
    except mysql.connector.Error as err:
        print(f"❌ Database setup error: {err}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

def fulfill_request(cursor, connection, blood_type, units_needed, request_id):
    today = datetime.today().date()
    compatible_types = BLOOD_COMPATIBILITY[blood_type]
    placeholders = ', '.join(['%s'] * len(compatible_types))
    
    query = f"""
        SELECT blood_id, blood_type 
        FROM units2 
        WHERE blood_type IN ({placeholders})
        AND status = 'active' 
        AND expiration_date > %s
        ORDER BY 
            CASE blood_type
                WHEN %s THEN 0
                ELSE 1
            END,
            expiration_date ASC
        LIMIT %s
    """

    params = compatible_types + [today.strftime('%Y-%m-%d'), blood_type, units_needed]
    cursor.execute(query, params)
    compatible_units = cursor.fetchall()

    if compatible_units and len(compatible_units) >= units_needed:
        for unit in compatible_units[:units_needed]:
            blood_id, _ = unit
            cursor.execute("UPDATE units2 SET status = 'used' WHERE blood_id = %s", (blood_id,))
        cursor.execute("UPDATE blood_requests SET status = 'approved' WHERE id = %s", (request_id,))
        connection.commit()
        print(f"✅ Request {request_id} approved.")
        return True
    else:
        print(f"⚠ Not enough compatible units for request {request_id}.")
        return False

def insert_and_process_requests(location, hospital_name, contact_number, request_date, blood_types, units_requested):
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        approved_requests = []

        for blood_type, units_needed in zip(blood_types, units_requested):
            cursor.execute("""
                INSERT INTO blood_requests 
                (location, hospital_name, contact_number, request_date, blood_type, units_requested)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (location, hospital_name, contact_number, request_date, blood_type, units_needed))
            connection.commit()

            request_id = cursor.lastrowid
            print(f"Processing request ID {request_id} for {blood_type}...")
            if fulfill_request(cursor, connection, blood_type, units_needed, request_id):
                approved_requests.append(request_id)

        return approved_requests
    except mysql.connector.Error as err:
        print(f"❌ Database error: {err}")
        return []
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

def process_approved_requests():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM blood_requests WHERE status = 'approved'")
        approved_requests = cursor.fetchall()

        if not approved_requests:
            print("No approved requests to process.")
            return

        for request in approved_requests:
            request_id, blood_type, request_date, location, hospital_name, contact_number, status, units_requested = request
            print(f"Processing approved request {request_id} for {blood_type}...")

            cursor.execute(""" 
                SELECT blood_id, quantity_ml, expiration_date 
                FROM units2 
                WHERE blood_type = %s AND status = 'used' 
                ORDER BY expiration_date ASC
                LIMIT %s
            """, (blood_type, units_requested))
            blood_records = cursor.fetchall()

            for blood_id, quantity_ml, expiration_date in blood_records:
                data = (
                    f"Blood Bank: LifeCare Blood Bank\n"
                    f"Blood Type: {blood_type}\n"
                    f"Expiration Date: {expiration_date}\n"
                    f"Hospital: {hospital_name}\n"
                    f"Location: {location}\n"
                    f"Blood ID: {blood_id}"
                )
                donor_name = f"{hospital_name}_{blood_id}"
                QRCodeGenerator.generate(data, donor_name, output_dir="qr_codes")
                cursor.execute("UPDATE units2 SET status = 'delivered' WHERE blood_id = %s", (blood_id,))
                connection.commit()

            cursor.execute("UPDATE blood_requests SET status = 'completed' WHERE id = %s", (request_id,))
            connection.commit()
            print(f"✅ Request {request_id} completed and QR codes generated.")
    except mysql.connector.Error as err:
        print(f"❌ Database error: {err}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

class DonationWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Blood Donation")
        self.geometry("900x700")
        
        # Add your donation form widgets here
        tk.Label(self, text="Blood Donation Form", font=('Helvetica', 20)).pack(pady=20)
        
        # Example form field
        tk.Label(self, text="Donor Name:").pack()
        self.name_entry = tk.Entry(self)
        self.name_entry.pack()
        
        # Add more form fields as needed...
        
        submit_btn = tk.Button(self, text="Submit Donation", command=self.submit_donation)
        submit_btn.pack(pady=20)
        
        # Center window
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'+{x}+{y}')
        
        # Make window modal
        self.grab_set()
    
    def submit_donation(self):
        # Handle form submission
        donor_name = self.name_entry.get()
        messagebox.showinfo("Success", f"Thank you for donating, {donor_name}!")
        self.destroy()

class BloodRequestApp(tk.Toplevel):  # Changed from tk.Tk to tk.Toplevel
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Blood Bank Request System")
        self.geometry("600x500")
        self.resizable(False, False)
        
        self.create_widgets()
        setup_database()
        
        # Center the window
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'+{x}+{y}')
        
        # Make window modal
        self.grab_set()

    def create_widgets(self):
        title = tk.Label(self, text="Blood Request Form", font=("Arial", 18, "bold"))
        title.pack(pady=10)

        frame = tk.Frame(self)
        frame.pack(pady=5)

        tk.Label(frame, text="Hospital Name:").grid(row=0, column=0, sticky="e")
        self.hospital_entry = tk.Entry(frame, width=30)
        self.hospital_entry.grid(row=0, column=1, padx=10)

        tk.Label(frame, text="Location:").grid(row=1, column=0, sticky="e")
        self.location_entry = tk.Entry(frame, width=30)
        self.location_entry.grid(row=1, column=1, padx=10)

        tk.Label(frame, text="Contact Number:").grid(row=2, column=0, sticky="e")
        self.contact_entry = tk.Entry(frame, width=30)
        self.contact_entry.grid(row=2, column=1, padx=10)

        tk.Label(frame, text="Request Date (YYYY-MM-DD):").grid(row=3, column=0, sticky="e")
        self.date_entry = tk.Entry(frame, width=30)
        self.date_entry.grid(row=3, column=1, padx=10)

        self.blood_frame = tk.Frame(self)
        self.blood_frame.pack(pady=10)
        self.blood_entries = []

        add_btn = tk.Button(self, text="Add Blood Type", command=self.add_blood_type_row)
        add_btn.pack(pady=5)

        self.submit_btn = tk.Button(self, text="Submit Request", command=self.submit_request)
        self.submit_btn.pack(pady=10)

    def add_blood_type_row(self):
        row = len(self.blood_entries)
        blood_type_var = tk.StringVar()
        unit_var = tk.IntVar()

        tk.Label(self.blood_frame, text="Blood Type:").grid(row=row, column=0, padx=5)
        blood_menu = ttk.Combobox(self.blood_frame, textvariable=blood_type_var, values=sorted(VALID_BLOOD_GROUPS), width=5)
        blood_menu.grid(row=row, column=1, padx=5)

        tk.Label(self.blood_frame, text="Units:").grid(row=row, column=2, padx=5)
        unit_entry = tk.Entry(self.blood_frame, textvariable=unit_var, width=5)
        unit_entry.grid(row=row, column=3, padx=5)

        self.blood_entries.append((blood_type_var, unit_var))

    def submit_request(self):
        hospital = self.hospital_entry.get()
        location = self.location_entry.get()
        contact = self.contact_entry.get()
        request_date = self.date_entry.get()

        if not (hospital and location and contact and request_date):
            messagebox.showerror("Input Error", "All fields must be filled.")
            return
        if not contact.isdigit() or len(contact) != 10:
            messagebox.showerror("Input Error", "Contact must be a 10-digit number.")
            return
        try:
            datetime.strptime(request_date, '%Y-%m-%d')
        except ValueError:
            messagebox.showerror("Date Error", "Invalid date format. Use YYYY-MM-DD.")
            return

        blood_types, units_requested = [], []
        for blood_type_var, unit_var in self.blood_entries:
            b_type = blood_type_var.get().upper()
            try:
                unit_val = int(unit_var.get())
            except:
                continue
            if b_type in VALID_BLOOD_GROUPS and unit_val > 0:
                blood_types.append(b_type)
                units_requested.append(unit_val)

        if not blood_types:
            messagebox.showerror("Input Error", "Add at least one valid blood type and unit.")
            return

        approved = insert_and_process_requests(location, hospital, contact, request_date, blood_types, units_requested)

        if approved:
            process_approved_requests()
            messagebox.showinfo("Success", f"Request submitted and QR codes generated.")
        else:
            messagebox.showwarning("Incomplete", "Request submitted, but not fully approved.")
    
if __name__ == "__main__":
    app = BloodRequestApp()
    app.mainloop()