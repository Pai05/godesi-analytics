{% docs net_revenue_inr %}
**Net revenue (INR)**: the money GoDesi keeps from an order line.

`quantity × unit price − discount`, set to **0** when the line was cancelled or returned.
Marketplace commission is *not* subtracted here; it is in `commission_cost_inr`.
{% enddocs %}

{% docs gross_profit_inr %}
**Gross profit (INR)** = `net_revenue_inr − cogs_inr − commission_cost_inr`.

Can be negative: a returned marketplace order earns nothing but still costs the commission.
{% enddocs %}
