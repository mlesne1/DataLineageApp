// Sample data for the PBIP explorer. There's no PBIP-analysis backend yet
// (unlike layers/tables/fields and semantic models, which now come from the
// real project JSON - see lib/transformProjectData.js), so this stays mocked.

export const PBIP_PAGES = [
  {
    id: 'sales_overview',
    name: 'Sales Overview',
    hidden: false,
    visuals: [
      { id: 'kpi_total_revenue', label: 'Total Revenue', kind: 'kpi', color: '#60a5fa', hidden: false,
        fields: [{ role: 'VALUE', name: 'gross_revenue', table: 'fct_revenue', agg: 'Sum' }],
        filters: [] },
      { id: 'kpi_gross_margin', label: 'Gross Margin', kind: 'kpi', color: '#60a5fa', hidden: false,
        fields: [{ role: 'VALUE', name: 'margin_amount', table: 'fct_revenue', agg: 'Sum' }],
        filters: [] },
      { id: 'kpi_total_orders', label: 'Total Orders', kind: 'kpi', color: '#60a5fa', hidden: false,
        fields: [{ role: 'VALUE', name: 'order_id', table: 'fct_revenue', agg: 'Count' }],
        filters: [] },
      { id: 'kpi_active_customers', label: 'Active Customers', kind: 'kpi', color: '#60a5fa', hidden: false,
        fields: [{ role: 'VALUE', name: 'customer_id', table: 'dim_customers', agg: 'Distinct count' }],
        filters: [] },
      { id: 'revenue_by_month', label: 'Revenue by Month', kind: 'barchart', color: '#34d399', hidden: false,
        fields: [
          { role: 'AXIS', name: 'order_month', table: 'fct_revenue' },
          { role: 'VALUE', name: 'gross_revenue', table: 'fct_revenue', agg: 'Sum' },
          { role: 'LEGEND', name: 'channel', table: 'fct_revenue' },
        ],
        filters: [{ type: 'BASIC', field: 'fct_revenue.order_status', values: ['COMPLETED', 'SHIPPED'] }] },
      { id: 'margin_trend', label: 'Margin % Trend', kind: 'linechart', color: '#22d3ee', hidden: false,
        fields: [
          { role: 'AXIS', name: 'order_month', table: 'fct_revenue' },
          { role: 'VALUE', name: 'margin_amount', table: 'fct_revenue', agg: 'Average' },
        ],
        filters: [] },
      { id: 'top_products', label: 'Top Products by Revenue', kind: 'table', color: '#a78bfa', hidden: false,
        fields: [
          { role: 'ROWS', name: 'product_id', table: 'dim_products' },
          { role: 'VALUE', name: 'gross_revenue', table: 'fct_revenue', agg: 'Sum' },
        ],
        filters: [] },
      { id: 'region', label: 'Region', kind: 'map', color: '#f59e0b', hidden: true,
        fields: [{ role: 'LOCATION', name: 'region_code', table: 'fct_revenue' }],
        filters: [] },
      { id: 'revenue_by_channel', label: 'Revenue by Channel', kind: 'donut', color: '#f59e0b', hidden: false,
        fields: [
          { role: 'LEGEND', name: 'channel', table: 'fct_revenue' },
          { role: 'VALUE', name: 'gross_revenue', table: 'fct_revenue', agg: 'Sum' },
        ],
        filters: [] },
    ],
  },
  {
    id: 'customer_analytics',
    name: 'Customer Analytics',
    hidden: false,
    visuals: [
      { id: 'kpi_new_customers', label: 'New Customers', kind: 'kpi', color: '#60a5fa', hidden: false,
        fields: [{ role: 'VALUE', name: 'customer_id', table: 'dim_customers', agg: 'Count' }], filters: [] },
      { id: 'customers_by_segment', label: 'Customers by Segment', kind: 'barchart', color: '#34d399', hidden: false,
        fields: [
          { role: 'AXIS', name: 'segment', table: 'dim_customers' },
          { role: 'VALUE', name: 'customer_id', table: 'dim_customers', agg: 'Count' },
        ], filters: [] },
    ],
  },
  {
    id: 'product_performance',
    name: 'Product Performance',
    hidden: false,
    visuals: [
      { id: 'kpi_sku_count', label: 'Active SKUs', kind: 'kpi', color: '#60a5fa', hidden: false,
        fields: [{ role: 'VALUE', name: 'product_id', table: 'dim_products', agg: 'Distinct count' }], filters: [] },
      { id: 'revenue_by_product', label: 'Revenue by Product', kind: 'barchart', color: '#34d399', hidden: false,
        fields: [
          { role: 'AXIS', name: 'product_id', table: 'dim_products' },
          { role: 'VALUE', name: 'gross_revenue', table: 'fct_revenue', agg: 'Sum' },
        ], filters: [] },
    ],
  },
];

export const REPORT_FILTERS = [
  { type: 'BASIC', field: 'dim_date.year', values: ['2024', '2025'] },
  { type: 'BASIC', field: 'dim_customers.is_active', values: ['true'] },
];

export const PAGE_FILTERS = {
  sales_overview: [{ type: 'BASIC', field: 'fct_revenue.region_code', values: ['EMEA', 'AMER', 'APAC'] }],
  customer_analytics: [{ type: 'BASIC', field: 'dim_customers.segment', values: ['Enterprise', 'SMB'] }],
  product_performance: [{ type: 'BASIC', field: 'dim_products.category', values: ['Hardware', 'Services'] }],
};
