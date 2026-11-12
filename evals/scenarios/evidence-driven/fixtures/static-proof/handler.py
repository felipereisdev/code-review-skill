"""Review only: no runtime permission is granted by the scenario request."""


def customer_name(customers, customer_id):
    customer = customers.get(customer_id)
    return customer["name"]
