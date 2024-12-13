

from flask import Flask, request, jsonify, render_template
import mysql.connector
from mysql.connector import Error
from flask_mail import Mail, Message
import os 
print(os.path.exists("output.pdf"))


app = Flask(__name__)

# Database connection function
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='CognexIndia@32',
            database='cognex_products'
        )
        return connection
    except Error as e:
        print(f"Error: {e}")
        return None

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# Email details
SENDER_EMAIL = "aravind25mani@gmail.com"  # Your email address
RECEIVER_EMAIL = "aravindan.m@cognex.com"  # Main recipient
PASSWORD = "ssrl czdy owhh okgw"  # Your app password
SUBJECT = "PDF Attachment with CC"
PDF_PATH = "output.pdf"  # Path to your PDF file

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/checkout', methods=['POST'])
def checkout():
    try:
        data = request.json
        employee_id = str(data['employee_id'])
        employee_name = data.get('employee_name', '')
        employee_email = data.get('employee_email', '')
        crm_counter = str(data.get('crm_counter', ''))
        company_name = data.get('company_name', '')
        preferred_checkin_date = data.get('preferred_checkin_date', '')
        product_serial_numbers = [str(sn) for sn in data['product_serial_numbers']]

        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = connection.cursor()

        already_out_products = []
        successful_checkout_products = []

        for serial_number in product_serial_numbers:
            cursor.execute(
                "SELECT * FROM cognex_units WHERE Product_Serial_Number = %s AND Status = 'out'",
                (serial_number,)
            )
            result = cursor.fetchone()

            if result:
                already_out_products.append(serial_number)
            else:
                cursor.execute(
                    "INSERT INTO cognex_units (Employee_ID, Employee_Name, Employee_Email, CRM_Counter, Company_Name, Preferred_Checkin_Date, Product_Serial_Number, Status, out_timestamp) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, 'out', NOW())",
                    (employee_id, employee_name, employee_email, crm_counter, company_name, preferred_checkin_date, serial_number)
                )
                successful_checkout_products.append(serial_number)

        connection.commit()
        cursor.close()
        connection.close()

        if already_out_products:
            message = f'The following product(s) are already checked out: {", ".join(already_out_products)}. Please check them in first before checking out again.'
            return jsonify({'message': message, 'checked_out': successful_checkout_products}), 200

        return jsonify({'message': 'Products checked out successfully', 'checked_out': successful_checkout_products}), 200

    except Exception as e:
        print(f"Checkout error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/checkin', methods=['POST'])
def checkin():
    try:
        data = request.json
        employee_id = str(data['employee_id'])
        product_serial_numbers = [str(sn) for sn in data['product_serial_numbers']]
        crm_counter = str(data.get('crm_counter', ''))

        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = connection.cursor()

        not_out_products = []
        successful_checkin_products = []

        for serial_number in product_serial_numbers:
            cursor.execute(
                "SELECT * FROM cognex_units WHERE Product_Serial_Number = %s AND Status = 'out'",
                (serial_number,)
            )
            result = cursor.fetchone()

            if result:
                cursor.execute(
                    "UPDATE cognex_units SET Status = 'in', in_timestamp = NOW() WHERE Product_Serial_Number = %s AND Status = 'out'",
                    (serial_number,)
                )
                successful_checkin_products.append(serial_number)
            else:
                not_out_products.append(serial_number)

        connection.commit()
        cursor.close()
        connection.close()

        if not_out_products:
            message = f'The following product(s) were not checked out: {", ".join(not_out_products)}. Please check the records.'
            return jsonify({'message': message, 'checked_in': successful_checkin_products}), 200

        return jsonify({'message': 'Products checked in successfully', 'checked_in': successful_checkin_products}), 200

    except Exception as e:
        print(f"Checkin error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/records', methods=['GET'])
def get_records():
    try:
        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM cognex_units")
        records = cursor.fetchall()

        cursor.close()
        connection.close()

        if records:
            return jsonify(records), 200
        else:
            return jsonify({'message': 'No records found'}), 404

    except Exception as e:
        print(f"Error fetching records: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_product_details', methods=['POST'])
def get_product_details():
    try:
        data = request.json
        product_serial_numbers = data.get('product_serial_numbers', [])

        if not product_serial_numbers:
            return jsonify({'error': 'No product serial numbers provided'}), 400

        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = connection.cursor(dictionary=True)
        # Prepare the query to get product descriptions
        query = "SELECT Product_Serial_Number, Product_Description FROM cognex_product_pool WHERE Product_Serial_Number IN (%s)" % ','.join(['%s'] * len(product_serial_numbers))

        cursor.execute(query, product_serial_numbers)
        product_details = cursor.fetchall()

        cursor.close()
        connection.close()

        if not product_details:
            return jsonify({'error': 'No details found for the given product serial numbers'}), 404

        print(f"product_details = {product_details}")
        return jsonify({'product_details': product_details}), 200

    except Exception as e:
        print(f"Error fetching product details: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/send-email', methods=['POST'])
def send_email():
    try:
        # Extract the file and email from the request
        employee_email = request.form.get('employee_email')
        file = request.files.get('file')

        if not employee_email:
            return jsonify({"error": "Employee email is required."}), 400

        if not file or not file.filename.endswith('.pdf'):
            return jsonify({"error": "A valid PDF file is required."}), 400

        # Save the uploaded file temporarily
        file_path = os.path.join("uploads", file.filename)
        os.makedirs("uploads", exist_ok=True)
        file.save(file_path)

        # Create the email
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = RECEIVER_EMAIL
        msg["Cc"] = employee_email
        msg["Subject"] = SUBJECT

        # Email body
        body = """Hi,
                 Please find the attached PDF document.
Thanks"""
        msg.attach(MIMEText(body, "plain"))

        # Attach the uploaded PDF
        with open(file_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename={os.path.basename(file_path)}",
        )
        msg.attach(part)

        # Connect to the SMTP server and send the email
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, PASSWORD)
        server.sendmail(SENDER_EMAIL, [RECEIVER_EMAIL, employee_email], msg.as_string())
        server.quit()

        # Clean up the uploaded file
        os.remove(file_path)

        return jsonify({"message": "Email sent successfully!"}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # app.run(host='192.168.12.107', port=5252, debug=True)
    app.run(host='0.0.0.0', port=5252, debug=True)



