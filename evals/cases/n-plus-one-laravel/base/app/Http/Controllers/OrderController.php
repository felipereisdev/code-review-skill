<?php

namespace App\Http\Controllers;

use App\Models\Order;
use Illuminate\View\View;

class OrderController extends Controller
{
    public function index(): View
    {
        $orders = Order::query()
            ->latest()
            ->paginate(25);

        return view('orders.index', ['orders' => $orders]);
    }
}
