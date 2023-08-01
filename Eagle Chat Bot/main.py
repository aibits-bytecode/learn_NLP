from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse
import db_helper
import generic_helper

app = FastAPI()

global inprogress_orders
inprogress_orders = {}


# uvicorn main:app --reload
@app.post('/')
async def handle_request(request: Request):
    # Parse the JSON data received from Dialogflow
    payload = await request.json()

    # Extract relevant information from the JSON data
    intent = payload["queryResult"]["intent"]["displayName"]
    parameters = payload["queryResult"]["parameters"]
    output_contexts = payload['queryResult']['outputContexts']

    session_id = generic_helper.extract_session_id(output_contexts[0]["name"])

    intent_handler_dict = {
        'order.add': add_to_order,
        'order.remove': remove_from_order,
        'order.complete': complete_order,
        'track.order - context': track_order
    }

    return intent_handler_dict[intent](parameters, session_id)


def save_to_db(order):
    # Need to get max order_id and +1
    next_order_id = db_helper.get_next_order_id()
    # Insert individual items along with quantity in orders table
    for food_item, quantity in order.items():
        rcode = db_helper.insert_order_item(
            food_item,
            quantity,
            next_order_id
        )

        if rcode == -1:
            return -1

    # Now insert order tracking status
    db_helper.insert_order_tracking(next_order_id, "in progress")

    return next_order_id


def complete_order(parameter: dict, session_id):
    if session_id not in inprogress_orders:
        fulfillment_text = f"Please re enter the order we didn't get your order"
    else:
        # save the order in db
        order = inprogress_orders[session_id]
        order_id = save_to_db(order)
        if order_id == -1:
            fulfillment_text = f"Please come later there is issue in saving the order"
        else:
            order_total = db_helper.get_total_order_price(order_id)
            fulfillment_text = f"Your order is places and your order id : {order_id} and price : {order_total}"
    del inprogress_orders[session_id]
    return JSONResponse(content={
        "fulfillmentText": fulfillment_text
    })


def add_to_order(parameters: dict, session_id):
    food_items = parameters['food-item']
    quantities = parameters['number']

    if len(food_items) != len(quantities):
        fulfillment_text = f"Please add the quantity for each food item"
    else:
        # Using zip and dictionary comprehension
        new_food_dict = {food: qty for food, qty in zip(food_items, quantities)}
        if session_id in inprogress_orders:
            old_food_dict = inprogress_orders[session_id]
            old_food_dict.update(new_food_dict)
            inprogress_orders[session_id] = old_food_dict
        else:
            inprogress_orders[session_id] = new_food_dict

        order_str = generic_helper.get_str_from_food_dict(inprogress_orders[session_id])
        fulfillment_text = f"So far you have: {order_str}. Do you need anything else?"

    return JSONResponse(content={
        "fulfillmentText": fulfillment_text
    })


def remove_from_order(parameters: dict, session_id: str):
    if session_id not in inprogress_orders:
        return JSONResponse(content={
            "fulfillmentText": "I'm having a trouble finding your order. Sorry! Can you place a new order please?"
        })

    food_items = parameters["food-item"]

    removed_items = []
    no_such_items = []

    for item in food_items:
        if item not in inprogress_orders[session_id]:
            no_such_items.append(item)
        else:
            removed_items.append(item)
            del inprogress_orders[session_id][item]

    if len(removed_items) > 0:
        fulfillment_text = f'Removed {",".join(removed_items)} from your order!'

    if len(no_such_items) > 0:
        fulfillment_text = f' Your current order does not have {",".join(no_such_items)}'

    if len(inprogress_orders[session_id].keys()) == 0:
        fulfillment_text += " Your order is empty!"
    else:
        order_str = generic_helper.get_str_from_food_dict(inprogress_orders[session_id])
        fulfillment_text += f" Here is what is left in your order: {order_str}"

    return JSONResponse(content={
        "fulfillmentText": fulfillment_text
    })


def track_order(parameter: dict, session_id):
    order_id = int(parameter['orderid'])
    order_status = db_helper.get_order_status(order_id)
    if order_status:
        fulfillment_text = f"The order status for order id: {order_id} is: {order_status}"
    else:
        fulfillment_text = f"No order found with order id: {order_id}"

    return JSONResponse(content={
        "fulfillmentText": fulfillment_text
    })
