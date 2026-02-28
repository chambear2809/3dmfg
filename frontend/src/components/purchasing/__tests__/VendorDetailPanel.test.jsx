import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import VendorDetailPanel from '../VendorDetailPanel'
import { MockLocaleProvider } from '../../../test/mockLocaleProvider'

// VendorDetailPanel fetches /vendors/:id/metrics on mount.
// Mock fetch to return controlled metrics including total_spend and recent_pos.
beforeEach(() => {
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      total_pos: 3,
      total_spend: 1500.00,
      avg_lead_time_days: 7,
      on_time_delivery_pct: 95,
      recent_pos: [
        {
          id: 1,
          po_number: 'PO-042',
          order_date: '2026-01-10',
          total_amount: 500.00,
          status: 'received',
        },
      ],
    }),
  })
})

const vendor = {
  id: 42,
  name: 'Acme Supplies',
  code: 'ACME',
  is_active: true,
  contact_name: null,
  email: null,
  phone: null,
  website: null,
  address_line1: null,
  city: null,
  payment_terms: null,
  account_number: null,
  notes: null,
}

const renderWith = (currency, locale = 'en-US') =>
  render(
    <MockLocaleProvider currency={currency} locale={locale}>
      <VendorDetailPanel
        vendor={vendor}
        onClose={vi.fn()}
        onEdit={vi.fn()}
        onCreatePO={vi.fn()}
        onViewPO={vi.fn()}
      />
    </MockLocaleProvider>
  )

describe('VendorDetailPanel — currency display', () => {
  it('shows $ with USD for total_spend after metrics load', async () => {
    renderWith('USD')
    expect(await screen.findByText('$1,500.00')).toBeInTheDocument()
  })

  it('shows € instead of $ with EUR for total_spend', async () => {
    renderWith('EUR')
    expect(await screen.findByText('€1,500.00')).toBeInTheDocument()
    expect(screen.queryByText('$1,500.00')).not.toBeInTheDocument()
  })

  it('shows £ instead of $ with GBP for total_spend', async () => {
    renderWith('GBP')
    expect(await screen.findByText('£1,500.00')).toBeInTheDocument()
    expect(screen.queryByText('$1,500.00')).not.toBeInTheDocument()
  })

  it('shows $ with USD for recent PO total_amount', async () => {
    renderWith('USD')
    expect(await screen.findByText('$500.00')).toBeInTheDocument()
  })

  it('shows € instead of $ with EUR for recent PO total_amount', async () => {
    renderWith('EUR')
    expect(await screen.findByText('€500.00')).toBeInTheDocument()
    expect(screen.queryByText('$500.00')).not.toBeInTheDocument()
  })
})
