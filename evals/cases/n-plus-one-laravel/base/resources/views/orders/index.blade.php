<table>
    @foreach ($orders as $order)
        <tr>
            <td>{{ $order->number }}</td>
            <td>{{ $order->created_at->toDateString() }}</td>
        </tr>
    @endforeach
</table>
{{ $orders->links() }}
