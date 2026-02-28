import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import PODetailModal from '../PODetailModal'
import { MockLocaleProvider } from '../../../test/mockLocaleProvider'

// Mock child components that make API calls
vi.mock('../../POActivityTimeline', () => ({
  default: () => <div data-testid="activity-timeline" />,
}))
vi.mock('../DocumentUploadPanel', () => ({
  default: () => <div data-testid="document-upload" />,
}))

// Suppress fetch calls from the Modal's sub-components
beforeEach(() => {
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => [],
  })
})

const po = {
  id: 1,
  po_number: 'PO-001',
  vendor_name: 'Test Vendor',
  status: 'ordered',
  order_date: '2026-01-15',
  expected_date: null,
  shipped_date: null,
  received_date: null,
  tracking_number: null,
  carrier: null,
  notes: null,
  subtotal: '90.00',
  tax_amount: '0.00',
  shipping_cost: '10.00',
  total_amount: '100.00',
  lines: [
    {
      id: 1,
      line_number: 1,
      product_sku: 'SKU-001',
      product_name: 'Test Item',
      quantity_ordered: '3.00',
      quantity_received: '0.00',
      unit_cost: '30.00',
      line_total: '90.00',
    },
  ],
}

const renderWith = (currency, locale = 'en-US') =>
  render(
    <MockLocaleProvider currency={currency} locale={locale}>
      <PODetailModal
        po={po}
        onClose={vi.fn()}
        onStatusChange={vi.fn()}
        onEdit={vi.fn()}
        onReceive={vi.fn()}
      />
    </MockLocaleProvider>
  )

describe('PODetailModal — currency display', () => {
  it('shows $ with USD for unit_cost', () => {
    renderWith('USD')
    expect(screen.getByText('$30.00')).toBeInTheDocument()
  })

  it('shows € instead of $ with EUR for unit_cost', () => {
    renderWith('EUR')
    expect(screen.getByText('€30.00')).toBeInTheDocument()
    expect(screen.queryByText('$30.00')).not.toBeInTheDocument()
  })

  it('shows £ instead of $ with GBP for unit_cost', () => {
    renderWith('GBP')
    expect(screen.getByText('£30.00')).toBeInTheDocument()
    expect(screen.queryByText('$30.00')).not.toBeInTheDocument()
  })

  it('shows $ with USD for total_amount', () => {
    renderWith('USD')
    expect(screen.getByText(/Total:\s*\$100\.00/)).toBeInTheDocument()
  })

  it('shows € instead of $ with EUR for total_amount', () => {
    renderWith('EUR')
    expect(screen.getByText(/Total:\s*€100\.00/)).toBeInTheDocument()
    expect(screen.queryByText(/Total:\s*\$100\.00/)).not.toBeInTheDocument()
  })

  it('shows $ with USD for subtotal', () => {
    renderWith('USD')
    expect(screen.getByText(/Subtotal:\s*\$90\.00/)).toBeInTheDocument()
  })

  it('shows € instead of $ with EUR for subtotal', () => {
    renderWith('EUR')
    expect(screen.getByText(/Subtotal:\s*€90\.00/)).toBeInTheDocument()
    expect(screen.queryByText(/Subtotal:\s*\$90\.00/)).not.toBeInTheDocument()
  })
})
