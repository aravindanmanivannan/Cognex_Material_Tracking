

from flask import Flask, request, jsonify, render_template
import mysql.connector
from mysql.connector import Error

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/checkout', methods=['POST'])
def checkout():
    try:
        data = request.json
        employee_id = str(data['employee_id'])
        employee_name = data.get('employee_name', '')
        crm_counter = str(data.get('crm_counter', ''))
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
                    "INSERT INTO cognex_units (Employee_ID, Employee_Name, CRM_Counter, Product_Serial_Number, Status, out_timestamp) "
                    "VALUES (%s, %s, %s, %s, 'out', NOW())",
                    (employee_id, employee_name, crm_counter, serial_number)
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

if __name__ == '__main__':
    # app.run(host='192.168.12.107', port=5252, debug=True)
    app.run(host='0.0.0.0', port=5252, debug=True)



