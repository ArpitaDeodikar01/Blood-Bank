import pandas as pd
import numpy as np
import mysql.connector
import sys
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import datetime
from PIL import Image, ImageDraw, ImageFont
import cv2
import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image, ImageTk
from sklearn.metrics import accuracy_score  # Add this import at the top
# ----------------------------
# Existing Classes (Unchanged)
# ----------------------------
class BloodDonorPredictor:
    def __init__(self, model=None):
        self.model = model
        self.columns = None
        self.user_data = None

    def load_data(self, filepath):
        try:
            df = pd.read_csv(filepath)
            df = df.dropna()
            df['gender'] = df['gender'].map({'Male': 1, 'Female': 0})
            df['last_donation_date'] = pd.to_datetime(df['last_donation_date'])
            df['days_since_last_donation'] = (pd.to_datetime('today') - df['last_donation_date']).dt.days
            df = df.drop(columns=['donor_id', 'name', 'contact_number', 'last_donation_date', 'blood_type', 'location'])
            X = df.drop(columns=['elgibility'])
            y = df['elgibility']
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.35, random_state=42)
            self.model = RandomForestClassifier(random_state=42)
            self.model.fit(X_train, y_train)
            self.columns = X_train.columns.tolist()
            print("✅ Model trained successfully.")
             # 🔍 Accuracy calculation
            y_pred = self.model.predict(X_test)
            acc = accuracy_score(y_test, y_pred)
            print(f"✅ Model trained successfully with accuracy: {acc:.2f}")
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            sys.exit(1)

    def predict(self):
        try:
            self.user_data = self.user_data[self.columns]
            prediction = self.model.predict(self.user_data)
            result = "Eligible" if prediction[0] == 1 else "Not Eligible"
            print(f"\n✅ Eligibility Prediction: {result}")
            
            return result
        except Exception as e:
            print(f"❌ Error during prediction: {e}")
            return "Not Eligible"

class DonorRegistration:
    def __init__(self):
        try:
            self.conn = mysql.connector.connect(
                host="localhost",
                user="root",
                password="root",
                database="blood"
            )
            self.cursor = self.conn.cursor()
        except mysql.connector.Error as err:
            print(f"❌ Database connection error: {err}")
            sys.exit(1)
        
    def register_donor(self, predictor: BloodDonorPredictor, eligibility, personal_info):
        insert_query = '''
            INSERT INTO donor_registration 
            (name, age, gender, hemoglobin_count, blood_type, last_donation_date, location, contact_number,
             weight, pulse_rate, blood_pressure, chronic_disorders, elgibility)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''
        user_values = predictor.user_data.iloc[0]
        values = (
            personal_info['name'],
            int(user_values['age']),
            'Male' if user_values['gender'] == 1 else 'Female',
            float(user_values['hemoglobin_count']),
            personal_info['blood_type'],
            personal_info['last_donation_date'],
            personal_info['location'],
            personal_info['contact_number'],
            float(user_values['weight']),
            int(user_values['pulse_rate']),
            int(user_values['blood_pressure']),
            int(user_values['chronic_disorders']),
            eligibility
        )

        try:
            self.cursor.execute(insert_query, values)
            self.conn.commit()
            print("\n✅ Donor Registered Successfully in Database!")
            
            self.cursor.execute("SELECT LAST_INSERT_ID()")
            donor_id = self.cursor.fetchone()[0]
            
            return donor_id, personal_info['blood_type'], personal_info['name']
        except mysql.connector.Error as err:
            print(f"\n❌ Error: {err}")
            return None, None, None

    def __del__(self):
        try:
            if hasattr(self, 'cursor') and self.cursor:
                self.cursor.close()
            if hasattr(self, 'conn') and self.conn and self.conn.is_connected():
                self.conn.close()
        except:
            pass

class BloodDonationRecorder:
    @staticmethod
    def insert_into_units2(donor_id, blood_type, quantity_ml):
        try:
            connection = mysql.connector.connect(
                host='localhost',
                user='root',
                password='root',
                database='blood'
            )
            cursor = connection.cursor()

            donation_date = datetime.datetime.today().date()
            expiration_date = donation_date + datetime.timedelta(days=30)

            cursor.execute("""
                INSERT INTO units2 (donor_id, blood_type, quantity_ml, donation_date, expiration_date, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (donor_id, blood_type, quantity_ml, donation_date, expiration_date, 'active'))
            
            connection.commit()

            print(f"✅ Blood unit inserted successfully for Donor ID {donor_id} ({blood_type}, {quantity_ml} ml).")
            return True, donation_date

        except mysql.connector.Error as err:
            print(f"❌ Error: {err}")
            return False, None

        finally:
            if 'connection' in locals() and connection.is_connected():
                cursor.close()
                connection.close()

class CertificateGenerator:
    @staticmethod
    def generate(donor_name, blood_type, donation_date, quantity_ml, output_dir="certificates"):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        template_path = r"D:\PSDL_ASSIGNMENT\BLOOD_BANK\BLOOD_BANK\certificate.jpg"
        try:
            image = cv2.imread(template_path)
            if image is None:
                raise FileNotFoundError("Certificate template not found")
        except Exception as e:
            print(f"❌ Error loading certificate template: {e}")
            return False

        pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_image)

        try:
            font_path = r"D:\PSDL_ASSIGNMENT\BLOOD_BANK\BLOOD_BANK\great-vibes\GreatVibes-Regular.ttf"
            name_font = ImageFont.truetype(font_path, 70)
            details_font = ImageFont.truetype(font_path, 40)
        except Exception as e:
            print(f"❌ Error loading fonts: {e}")
            return False

        name_text = donor_name
        name_bbox = draw.textbbox((0, 0), name_text, font=name_font)
        name_x = (pil_image.width - (name_bbox[2] - name_bbox[0])) / 2
        name_y = pil_image.height - 600
        draw.text((name_x, name_y), name_text, font=name_font, fill=(0, 0, 0))

        details_text = f"for donating {quantity_ml}ml of {blood_type} blood on {donation_date}"
        details_bbox = draw.textbbox((0, 0), details_text, font=details_font)
        details_x = (pil_image.width - (details_bbox[2] - details_bbox[0])) / 2
        details_y = name_y + 100
        draw.text((details_x, details_y), details_text, font=details_font, fill=(0, 0, 0))

        filename = f"{output_dir}/{donor_name.replace(' ', '_')}_{donation_date}.jpg"
        cv2.imwrite(filename, cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR))
        
        print(f"✅ Certificate generated successfully: {filename}")
        CertificateGenerator.show_certificate_popup(filename)
        return True
    
    @staticmethod
    def show_certificate_popup(image_path):
        popup = tk.Toplevel()
        popup.title("Donation Certificate")
        
        img = Image.open(image_path)
        photo = ImageTk.PhotoImage(img)
        
        label = tk.Label(popup, image=photo)
        label.image = photo
        label.pack()
        
        close_btn = ttk.Button(popup, text="Close", command=popup.destroy)
        close_btn.pack(pady=10)
        
        # Center window
        popup.update_idletasks()
        width = popup.winfo_width()
        height = popup.winfo_height()
        x = (popup.winfo_screenwidth() // 2) - (width // 2)
        y = (popup.winfo_screenheight() // 2) - (height // 2)
        popup.geometry(f'+{x}+{y}')

# ----------------------------
# New Tkinter Interface
# ----------------------------
class BloodBankApp:
    def __init__(self, root):
        self.root = root
        self.setup_window()
        self.create_main_menu()
        
    def setup_window(self):
        self.root.title("LifeSaver Blood Bank")
        self.root.geometry("1000x700")
        self.root.configure(bg="#f5f5f5")
        self.style = ttk.Style()
        self.style.configure('TButton', font=('Helvetica', 12), padding=10)
        
    def create_main_menu(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Header
        header = tk.Frame(self.root, bg="#ff6b6b", height=150)
        header.pack(fill='x')
        tk.Label(header, text="LifeSaver Blood Bank", font=('Helvetica', 28, 'bold'), 
                bg="#ff6b6b", fg="white").pack(pady=40)
        
        # Main Content
        content = tk.Frame(self.root, bg="#f5f5f5", padx=50, pady=50)
        content.pack(expand=True, fill='both')
        
        # Menu Buttons
        buttons = [
            ("💉 Donate Blood", self.open_donation),
            ("🏥 Collect Blood", self.open_collection),
            ("📊 View Database", self.open_database),
            ("📈 View Analytics", self.open_analytics)
        ]
        
        for text, command in buttons:
            btn = tk.Button(content, text=text, font=('Helvetica', 14), 
                          bg="#4ecdc4", fg="white", activebackground="#3dc9bf",
                          width=25, height=2, borderwidth=0, command=command)
            btn.pack(pady=15)
        
        # Footer
        footer = tk.Frame(self.root, bg="#dfe6e9", height=50)
        footer.pack(fill='x', side='bottom')
        tk.Button(footer, text="Exit", command=self.root.quit, 
                 bg="#ff6b6b", fg="white").pack(side='right', padx=20, pady=10)
    # In your BloodBankApp class, modify these methods:

    
    def open_analytics(self):
     try:
        from Graph import show_analytics_menu
        show_analytics_menu(self.root)  # Pass the root window as parent
     except ImportError as e:
        messagebox.showerror("Error", f"Cannot open Analytics: {str(e)}")
     except Exception as e:
        messagebox.showerror("Error", f"Failed to open analytics: {str(e)}")

        
    

    def open_collection(self):
     try:
        from Blood_Request import BloodRequestApp
        # Create a Toplevel window instead of a new Tk instance
        request_window = tk.Toplevel(self.root)
        request_app = BloodRequestApp(request_window)
        request_window.grab_set()  # Make it modal
     except ImportError as e:
        messagebox.showerror("Error", f"Cannot open Blood Collection: {str(e)}")
     except Exception as e:
        messagebox.showerror("Error", f"Failed to open collection module: {str(e)}")
    
    
    def open_database(self):
     #Open the database viewer window
     try:
        from Blood_Request import DatabaseViewer
        DatabaseViewer(self.root)
     except ImportError as e:
        messagebox.showerror("Error", f"Cannot open Database Viewer: {str(e)}")
     except Exception as e:
        messagebox.showerror("Error", f"Database connection failed: {str(e)}")
    
    def open_donation(self):
        DonationWindow(self.root)
    

class DonationWindow:
    def __init__(self, parent):
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title("Blood Donation")
        self.window.geometry("900x700")
        
        self.predictor = BloodDonorPredictor()
        try:
            self.predictor.load_data(r'C:\Users\LENOVO\Desktop\Blood_Bank_System\Donor.csv')
            self.show_health_form()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load model: {str(e)}")
            self.window.destroy()
    
    def show_health_form(self):
        self.clear_window()
        tk.Label(self.window, text="Health Information", font=('Helvetica', 20)).pack(pady=20)
        
        self.entries = {}
        fields = [
            ('age', 'Age (18-60)', 'int', (18, 60)),
            ('gender', 'Gender (0=Female, 1=Male)', 'int', (0, 1)),
            ('hemoglobin_count', 'Hemoglobin (g/dL)', 'float', (0, None)),
            ('days_since_last_donation', 'Days Since Last Donation', 'int', (0, None)),
            ('weight', 'Weight (kg)', 'float', (0, None)),
            ('pulse_rate', 'Pulse Normal? (1=Yes, 0=No)', 'int', (0, 1)),
            ('blood_pressure', 'BP Normal? (0=Yes, 1=No)', 'int', (0, 1)),
            ('chronic_disorders', 'Chronic Issues? (0=No, 1=Yes)', 'int', (0, 1))
        ]
        
        for field in fields:
            frame = tk.Frame(self.window)
            frame.pack(pady=5, fill='x', padx=50)
            
            tk.Label(frame, text=field[1], width=25, anchor='w').pack(side='left')
            entry = tk.Entry(frame)
            entry.pack(side='right', expand=True, fill='x')
            self.entries[field[0]] = (entry, field[2], field[3])
        
        tk.Button(self.window, text="Check Eligibility", command=self.check_eligibility,
                bg="#4ecdc4", fg="white").pack(pady=20)
    
    def check_eligibility(self):
        try:
            health_data = {}
            for field, (widget, dtype, range_) in self.entries.items():
                value = widget.get()
                
                if not value:
                    raise ValueError(f"Please enter {field}")
                
                if dtype == 'int':
                    value = int(value)
                elif dtype == 'float':
                    value = float(value)
                
                if range_[0] is not None and value < range_[0]:
                    raise ValueError(f"{field} must be ≥ {range_[0]}")
                if range_[1] is not None and value > range_[1]:
                    raise ValueError(f"{field} must be ≤ {range_[1]}")
                
                health_data[field] = value
            
            self.predictor.user_data = pd.DataFrame([health_data])
            result = self.predictor.predict()
            
            if result == "Eligible":
                self.show_personal_form()
            else:
                messagebox.showwarning("Not Eligible", "Sorry, this donor is not eligible")
        
        except ValueError as e:
            messagebox.showerror("Input Error", str(e))
    
    def show_personal_form(self):
        self.clear_window()
        tk.Label(self.window, text="Personal Information", font=('Helvetica', 20)).pack(pady=20)
        
        self.personal_entries = {}
        fields = [
            ('name', 'Full Name'),
            ('blood_type', 'Blood Type'),
            ('last_donation_date', 'Last Donation (YYYY-MM-DD)'),
            ('location', 'Location'),
            ('contact_number', 'Contact Number')
        ]
        
        for field in fields:
            frame = tk.Frame(self.window)
            frame.pack(pady=5, fill='x', padx=50)
            
            tk.Label(frame, text=field[1], width=25, anchor='w').pack(side='left')
            entry = tk.Entry(frame)
            entry.pack(side='right', expand=True, fill='x')
            self.personal_entries[field[0]] = entry
        
        tk.Button(self.window, text="Complete Donation", command=self.complete_donation,
                bg="#4ecdc4", fg="white").pack(pady=20)
    
    def complete_donation(self):
        try:
            personal_data = {}
            for field, widget in self.personal_entries.items():
                value = widget.get().strip()
                if not value:
                    raise ValueError(f"Please enter {field.replace('_', ' ')}")
                personal_data[field] = value
            
            if not personal_data['contact_number'].isdigit() or len(personal_data['contact_number']) != 10:
                raise ValueError("Contact number must be 10 digits")
            
            quantity = simpledialog.askinteger("Donation", "Enter quantity (ml):", 
                                            minvalue=1, maxvalue=500, parent=self.window)
            if not quantity:
                return
            
            registration = DonorRegistration()
            donor_id, blood_type, donor_name = registration.register_donor(
                self.predictor, "Eligible", personal_data)
            
            if donor_id:
                success, donation_date = BloodDonationRecorder.insert_into_units2(
                    donor_id, blood_type, quantity)
                
                if success:
                    CertificateGenerator.generate(
                        donor_name, blood_type, 
                        donation_date.strftime("%Y-%m-%d"), quantity)
                    messagebox.showinfo("Success", "Donation recorded successfully!")
                    self.window.destroy()
        
        except ValueError as e:
            messagebox.showerror("Input Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
    
    
    
    def clear_window(self):
        for widget in self.window.winfo_children():
            widget.destroy()

# ----------------------------
# Run the Application
# ----------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = BloodBankApp(root)
    root.mainloop()