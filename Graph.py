import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import tkinter as tk
from tkinter import simpledialog, messagebox, ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

def apply_plot_style():
    sns.set_theme(style="whitegrid")
    plt.rcParams['font.size'] = 12
    plt.rcParams['axes.labelsize'] = 14
    plt.rcParams['axes.titlesize'] = 16
    plt.rcParams['xtick.labelsize'] = 12
    plt.rcParams['ytick.labelsize'] = 12

def load_data(file_path):
    try:
        df = pd.read_csv(file_path)
        print(f"✅ Data successfully loaded from: {file_path}")
        return df
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return None

def plot_donors_by_blood_type(df, show=True):
    if df is None:
        return None
        
    fig = plt.figure(figsize=(10, 6))
    blood_type_counts = df['blood_type'].value_counts()
    sns.barplot(x=blood_type_counts.index, y=blood_type_counts.values, 
                palette="muted", edgecolor='black')

    for i, value in enumerate(blood_type_counts.values):
        plt.text(i, value + 0.5, int(value), ha='center', va='bottom', fontsize=11)

    plt.title('Number of Donors by Blood Type')
    plt.xlabel('Blood Type')
    plt.ylabel('Number of Donors')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    if show:
        plt.show()
    return fig

def plot_donations_by_month(df, show=True):
    if df is None:
        return None
        
    fig = plt.figure(figsize=(12, 6))
    df['last_donation_date'] = pd.to_datetime(df['last_donation_date'], format='%d-%m-%Y', errors='coerce')
    df['month_year'] = df['last_donation_date'].dt.strftime('%Y-%b')
    donation_counts = df['month_year'].value_counts().sort_index()

    sns.barplot(x=donation_counts.index, y=donation_counts.values, 
                palette="Blues_r", edgecolor='black')

    for i, value in enumerate(donation_counts.values):
        plt.text(i, value + 0.5, int(value), ha='center', va='bottom', fontsize=11)

    plt.title('Number of Donations by Month')
    plt.xlabel('Month-Year')
    plt.ylabel('Number of Donations')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    if show:
        plt.show()
    return fig

def plot_requested_vs_available(requests_df, donations_df, show=True):
    if requests_df is None or donations_df is None:
        return None
        
    fig = plt.figure(figsize=(12, 6))
    active_donations_df = donations_df[donations_df['status'].str.lower() == 'active']
    active_donations_df['units_available'] = active_donations_df['quantity_ml'] / 500

    available_units = active_donations_df.groupby('blood_type')['units_available'].sum().reset_index()
    requested_units = requests_df.groupby('blood_type')['units_requested'].sum().reset_index()

    units_comparison = pd.merge(requested_units, available_units, on='blood_type', how='outer').fillna(0)

    bar_width = 0.4
    x = range(len(units_comparison))

    plt.bar(x, units_comparison['units_requested'], width=bar_width, 
            label='Requested Units', color='salmon', edgecolor='black')
    plt.bar([p + bar_width for p in x], units_comparison['units_available'], 
            width=bar_width, label='Available Units', color='lightgreen', edgecolor='black')

    plt.xlabel('Blood Type')
    plt.ylabel('Units')
    plt.title('Blood Units: Requested vs Available')
    plt.xticks([p + bar_width/2 for p in x], units_comparison['blood_type'])
    plt.legend()
    plt.tight_layout()
    
    if show:
        plt.show()
    return fig

def show_analytics_menu(parent_window=None):
    """Show analytics selection menu"""
    apply_plot_style()
    
    # Load data
    donor_df = load_data(r"C:\Users\LENOVO\Desktop\Blood_Bank_System\Donor.csv")
    request_df = load_data(r"C:\Users\LENOVO\Desktop\Blood_Bank_System\blood_requests .csv")
    donation_df = load_data(r"C:\Users\LENOVO\Desktop\Blood_Bank_System\Blood_units_dataset.csv")
    
    # In standalone mode, use console menu
    if parent_window is None:
        while True:
            print("\n📊 MENU 📊")
            print("1. Show Number of Donors by Blood Type")
            print("2. Show Number of Donations by Month")
            print("3. Show Blood Units Requested vs Available")
            print("4. Exit")

            choice = input("Enter your choice (1-4): ").strip()

            if choice == '1':
                plot_donors_by_blood_type(donor_df)
            elif choice == '2':
                plot_donations_by_month(donor_df)
            elif choice == '3':
                plot_requested_vs_available(request_df, donation_df)
            elif choice == '4':
                print("👋 Exiting. Thank you!")
                break
            else:
                print("❌ Invalid choice. Please select 1-4.")
        return
    
    # In GUI mode, show dialog
    choice = simpledialog.askinteger(
        "Analytics Menu",
        "Choose an option:\n\n"
        "1. Show Donors by Blood Type\n"
        "2. Show Donations by Month\n"
        "3. Show Requested vs Available\n"
        "4. Show All\n\n"
        "Enter choice (1-4):",
        parent=parent_window,
        minvalue=1,
        maxvalue=4
    )
    
    if choice is None:  # User cancelled
        return
    
    # Create plot window
    plot_window = tk.Toplevel(parent_window)
    plot_window.title("Blood Bank Analytics")
    plot_window.geometry("1000x800")
    
    # Generate the selected plot(s)
    if choice == 1:
        fig = plot_donors_by_blood_type(donor_df, show=False)
    elif choice == 2:
        fig = plot_donations_by_month(donor_df, show=False)
    elif choice == 3:
        fig = plot_requested_vs_available(request_df, donation_df, show=False)
    elif choice == 4:
        fig = plt.figure(figsize=(12, 10))
        
        plt.subplot(2, 2, 1)
        plot_donors_by_blood_type(donor_df, show=False)
        
        plt.subplot(2, 2, 2)
        plot_donations_by_month(donor_df, show=False)
        
        plt.subplot(2, 1, 2)
        plot_requested_vs_available(request_df, donation_df, show=False)
        
        plt.tight_layout()
    
    # Display in Tkinter window
    canvas = FigureCanvasTkAgg(fig, master=plot_window)
    canvas.draw()
    canvas.get_tk_widget().pack(expand=True, fill='both')
    
    # Close button
    ttk.Button(plot_window, text="Close", command=plot_window.destroy).pack(pady=10)

if __name__ == "__main__":
    show_analytics_menu()