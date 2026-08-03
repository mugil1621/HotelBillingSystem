// ===============================
// HOTEL BILLING SYSTEM
// billing.js
// ===============================

let total = 0;
let totalItems = 0;


// ===============================
// Increase Quantity
// ===============================

function increase(button){

    let row = button.parentElement;

    let qtyBox = row.querySelector(".qty");

    qtyBox.value = parseInt(qtyBox.value) + 1;

    update();

}


// ===============================
// Decrease Quantity
// ===============================

function decrease(button){

    let row = button.parentElement;

    let qtyBox = row.querySelector(".qty");

    let qty = parseInt(qtyBox.value);

    if(qty > 0){

        qtyBox.value = qty - 1;

    }

    update();

}


// ===============================
// Update Total
// ===============================

function update(){

    total = 0;

    totalItems = 0;

    document.querySelectorAll(".qty").forEach(function(box){

        let qty = parseInt(box.value);

        if(isNaN(qty) || qty < 0){

            qty = 0;

            box.value = 0;

        }

        let price = parseFloat(box.dataset.price);

        totalItems += qty;

        total += qty * price;

    });

    document.getElementById("items").innerHTML = totalItems;

    document.getElementById("total").innerHTML = total.toFixed(2);

}


// ===============================
// Generate Bill
// ===============================

document.getElementById("billForm").onsubmit = function(){

    let bill = [];

    document.querySelectorAll(".qty").forEach(function(box){

        let qty = parseInt(box.value);

        if(qty > 0){

            bill.push({

                food_id: box.dataset.id,

                quantity: qty,

                price: box.dataset.price

            });

        }

    });

    if(bill.length === 0){

        alert("Please select at least one item.");

        return false;

    }

    document.getElementById("bill_data").value =
    JSON.stringify(bill);

    return true;

};