import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import CreateProductionOrderModal from '../CreateProductionOrderModal'
import { MockLocaleProvider } from '../../../test/mockLocaleProvider'

// Suppress any network calls the component might make
beforeEach(() => {
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({}),
  })
})

const bom = {
  product_id: 1,
  product_name: 'Bracket Assembly',
  product_sku: 'BA-001',
  code: 'BOM-001',
  version: 1,
  total_cost: '42.50',
  lines: [
    {
      id: 1,
      component_name: 'Steel Plate',
      component_unit: 'EA',
      quantity: '2',
      inventory_available: '10',
    },
  ],
}

const renderWith = (currency, locale = 'en-US') =>
  render(
    <MockLocaleProvider currency={currency} locale={locale}>
      <CreateProductionOrderModal
        bom={bom}
        quoteContext={null}
        onClose={vi.fn()}
        onSuccess={vi.fn()}
      />
    </MockLocaleProvider>
  )

describe('CreateProductionOrderModal — currency display', () => {
  // bom.total_cost renders in two places: "Unit Cost:" row and "Estimated Total Cost:" row
  // (quantity defaults to 1 so estimated = 1 * 42.50 = 42.50)
  // Use getAllByText since the value appears more than once.

  it('shows $ with USD for bom.total_cost', () => {
    renderWith('USD')
    expect(screen.getAllByText('$42.50').length).toBeGreaterThanOrEqual(1)
  })

  it('shows € instead of $ with EUR for bom.total_cost', () => {
    renderWith('EUR')
    expect(screen.getAllByText('€42.50').length).toBeGreaterThanOrEqual(1)
    expect(screen.queryByText('$42.50')).not.toBeInTheDocument()
  })

  it('shows £ instead of $ with GBP for bom.total_cost', () => {
    renderWith('GBP')
    expect(screen.getAllByText('£42.50').length).toBeGreaterThanOrEqual(1)
    expect(screen.queryByText('$42.50')).not.toBeInTheDocument()
  })

  it('renders the Estimated Total Cost label', () => {
    renderWith('USD')
    expect(screen.getByText('Estimated Total Cost:')).toBeInTheDocument()
  })

  it('shows € in Estimated Total Cost with EUR (no $ present)', () => {
    renderWith('EUR')
    expect(screen.getAllByText('€42.50').length).toBeGreaterThanOrEqual(1)
    expect(screen.queryByText('$42.50')).not.toBeInTheDocument()
  })
})
