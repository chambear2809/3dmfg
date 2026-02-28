import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ExplodedBOMView from '../ExplodedBOMView'
import { MockLocaleProvider } from '../../../test/mockLocaleProvider'

const explodedData = {
  total_components: 2,
  max_depth: 1,
  total_cost: '48.75',
  unique_components: 2,
  lines: [
    {
      level: 0,
      component_name: 'Frame Assembly',
      component_sku: 'FA-001',
      quantity_per_unit: 1.0,
      extended_quantity: 1.0,
      unit_cost: '20.00',
      line_cost: '40.00',
      is_sub_assembly: false,
      inventory_available: 5.0,
    },
    {
      level: 1,
      component_name: 'Bolt Set',
      component_sku: 'BS-002',
      quantity_per_unit: 4.0,
      extended_quantity: 4.0,
      unit_cost: '7.19',
      line_cost: '28.75',
      is_sub_assembly: false,
      inventory_available: 10.0,
    },
  ],
}

const renderWith = (currency, locale = 'en-US') =>
  render(
    <MockLocaleProvider currency={currency} locale={locale}>
      <ExplodedBOMView explodedData={explodedData} onClose={vi.fn()} />
    </MockLocaleProvider>
  )

describe('ExplodedBOMView — currency display', () => {
  it('shows $ with USD for total_cost', () => {
    renderWith('USD')
    expect(screen.getByText('$48.75')).toBeInTheDocument()
  })

  it('shows € instead of $ with EUR for total_cost', () => {
    renderWith('EUR')
    expect(screen.getByText('€48.75')).toBeInTheDocument()
    expect(screen.queryByText('$48.75')).not.toBeInTheDocument()
  })

  it('shows £ instead of $ with GBP for total_cost', () => {
    renderWith('GBP')
    expect(screen.getByText('£48.75')).toBeInTheDocument()
    expect(screen.queryByText('$48.75')).not.toBeInTheDocument()
  })

  it('shows $ with USD for line unit_cost', () => {
    renderWith('USD')
    expect(screen.getByText('$20.00')).toBeInTheDocument()
  })

  it('shows € instead of $ with EUR for line unit_cost', () => {
    renderWith('EUR')
    expect(screen.getByText('€20.00')).toBeInTheDocument()
    expect(screen.queryByText('$20.00')).not.toBeInTheDocument()
  })
})
