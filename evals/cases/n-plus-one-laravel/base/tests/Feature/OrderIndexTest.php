<?php

namespace Tests\Feature;

use App\Models\Order;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class OrderIndexTest extends TestCase
{
    use RefreshDatabase;

    public function test_it_lists_orders(): void
    {
        $order = Order::factory()->create();

        $this->actingAs(User::factory()->create())
            ->get('/orders')
            ->assertOk()
            ->assertSee($order->number)
            ->assertSee($order->customer->name);
    }
}
