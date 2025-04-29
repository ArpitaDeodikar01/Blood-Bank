import mysql.connector
import qrcode
from datetime import datetime
import os
import tkinter as tk
from tkinter import messagebox
import webbrowser
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


# Database configuration - adjust these settings to match your environment
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
            # Generate the QR code
            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill='black', back_color='white')

            # Create output directory if it doesn't exist
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # Save QR code as an image in the current directory
            filename = f"{donor_name.replace(' ', '_')}_qr.png"
            filepath = os.path.join(output_dir, filename) if output_dir else filename
            img.save(filepath)
            print(f"✅ QR Code generated and saved at: {filepath}")

            # Display QR code in a popup window
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

            # Open the saved QR code image
            img = Image.open(image_path)
            photo = ImageTk.PhotoImage(img)
            
            # Display the image in the popup
            label = tk.Label(popup, image=photo)
            label.image = photo  # Keep a reference!
            label.pack()

            close_btn = ttk.Button(popup, text="Close", command=popup.destroy)
            close_btn.pack(pady=10)

            # Center the popup window on the screen
            popup.update_idletasks()
            width = popup.winfo_width()
            height = popup.winfo_height()
            x = (popup.winfo_screenwidth() // 2) - (width // 2)
            y = (popup.winfo_screenheight() // 2) - (height // 2)
            popup.geometry(f'+{x}+{y}')
        except Exception as e:
            print(f"❌ Error displaying QR code image: {e}")


def setup_database():
    """Set up the database and create tables if they don't exist"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        # Create blood_units table (consistent naming)
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
        
        # Create blood_requests table
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
        return True
    except mysql.connector.Error as err:
        print(f"❌ Database setup error: {err}")
        return False
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()


def collect_hospital_data():
    """Collect hospital and blood request data from user input"""
    print("\n=== Blood Request Form ===")
    location = input("Enter location: ")
    hospital_name = input("Enter hospital name: ")

    while True:
        contact_number = input("Enter 10-digit contact number: ").strip()
        if contact_number.isdigit() and len(contact_number) == 10:
            break
        print("Invalid contact number. Please enter exactly 10 digits.")

    while True:
        request_date = input("Enter request date (YYYY-MM-DD): ")
        try:
            datetime.strptime(request_date, '%Y-%m-%d')
            break
        except ValueError:
            print("Invalid date format. Use YYYY-MM-DD.")

    blood_types, units_requested = [], []
    print("\nEnter blood types and units requested (type 'done' when finished):")
    while True:
        blood_type = input("Enter blood type (e.g., A+, O-, etc.) or 'done' to finish: ").upper()
        if blood_type.lower() == 'done':
            break
        if blood_type not in VALID_BLOOD_GROUPS:
            print(f"Invalid blood type. Valid types are: {', '.join(VALID_BLOOD_GROUPS)}")
            continue
        try:
            unit = int(input(f"Enter units requested for {blood_type}: "))
            if unit <= 0:
                print("Units must be positive.")
                continue
        except ValueError:
            print("Units must be a valid number.")
            continue
        blood_types.append(blood_type)
        units_requested.append(unit)

    if not blood_types:
        print("No valid blood types entered. Exiting.")
        return None

    return location, hospital_name, contact_number, request_date, blood_types, units_requested


def fulfill_request(cursor, connection, blood_type, units_needed, request_id):
    """Check if there are enough compatible blood units and fulfill the request if possible"""
    today = datetime.today().date()
    compatible_types = BLOOD_COMPATIBILITY[blood_type]

    # Format placeholders for SQL query
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
    
    # Parameters for the query
    params = compatible_types + [today.strftime('%Y-%m-%d'), blood_type, units_needed]
    
    cursor.execute(query, params)
    compatible_units = cursor.fetchall()

    if compatible_units and len(compatible_units) >= units_needed:
        for unit in compatible_units[:units_needed]:
            blood_id, _ = unit
            print(f"Using unit ID {blood_id}")
            cursor.execute("UPDATE units2 SET status = 'used' WHERE blood_id = %s", (blood_id,))
        
        cursor.execute("UPDATE blood_requests SET status = 'approved' WHERE id = %s", (request_id,))
        connection.commit()
        print(f"✅ Request {request_id} approved.")
        return True
    else:
        print(f"⚠ Not enough compatible units. Request {request_id} remains pending.")
        return False


def insert_and_process_requests(location, hospital_name, contact_number, request_date, blood_types, units_requested):
    """Insert blood requests into the database and try to fulfill them"""
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
            print(f"\nProcessing request ID {request_id} for {blood_type}...")
            
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
            print("MySQL connection closed.")


def process_approved_requests():
    """Process approved requests and generate QR codes"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM blood_requests WHERE status = 'approved'")
        approved_requests = cursor.fetchall()

        if not approved_requests:
            print("No approved requests to process.")
            return

        print(f"\nFound {len(approved_requests)} approved requests to process.")
        
        for request in approved_requests:
            request_id, blood_type, request_date, location, hospital_name, contact_number, status, units_requested = request
            print(f"\nProcessing approved request {request_id} for {blood_type}...")

            cursor.execute(""" 
                SELECT blood_id, quantity_ml, expiration_date 
                FROM units2 
                WHERE blood_type = %s AND status = 'used' 
                ORDER BY expiration_date ASC
                LIMIT %s
            """, (blood_type, units_requested))
            blood_records = cursor.fetchall()

            if not blood_records:
                print(f"No matching blood units found for request {request_id}.")
                continue

            for blood_id, quantity_ml, expiration_date in blood_records:
                # Generate the QR code here for each blood unit
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
                
                # Update the blood unit status to 'delivered'
                cursor.execute("UPDATE units2 SET status = 'delivered' WHERE blood_id = %s", (blood_id,))
                connection.commit()

            # Update the request status to 'completed'
            cursor.execute("UPDATE blood_requests SET status = 'completed' WHERE id = %s", (request_id,))
            connection.commit()
            print(f"✅ Request {request_id} processed and QR codes generated.")

    except mysql.connector.Error as err:
        print(f"❌ Database error: {err}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection closed.")


def check_database_connection():
    """Test the database connection"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            db_info = connection.get_server_info()
            print(f"✅ Connected to MySQL Server version {db_info}")
            
            cursor = connection.cursor()
            cursor.execute("SELECT DATABASE();")
            database_name = cursor.fetchone()[0]
            print(f"✅ Connected to database: {database_name}")
            return True
    except mysql.connector.Error as err:
        print(f"❌ Database connection error: {err}")
        return False
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection closed.")


def main():
    """Main function to run the blood bank management system"""
    print("\n" + "="*50)
    print("BLOOD BANK MANAGEMENT SYSTEM".center(50))
    print("Hospital Request Module".center(50))
    print("="*50 + "\n")

    # Check if database connection works
    if not check_database_connection():
        print("❌ Cannot connect to database. Please check your database settings.")
        return False
    
    # Setup database tables
    if not setup_database():
        print("❌ Failed to set up database. Exiting.")
        return False
    
    # Collect data and process requests
    result = collect_hospital_data()
    if not result:
        return False
        
    location, hospital_name, contact_number, request_date, blood_types, units_requested = result
    approved_requests = insert_and_process_requests(location, hospital_name, contact_number, request_date, blood_types, units_requested)
    
    if approved_requests:
        print("\nProcessing approved requests and generating QR codes...")
        process_approved_requests()
    
    return True


if __name__ == "__main__":
    try:
        while True:
            success = main()
            if not success:
                print("\nEncountered issues during execution.")
            
            another = input("\nMake another request? (yes/no): ").lower()
            if another != 'yes':
                print("\nThank you for using the Blood Bank System!")
                break
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
    finally:
        print("Program exited.\n")