import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import BOMLinesList from '../BOMLinesList'
import { MockLocaleProvider } from '../../../test/mockLocaleProvider'

const lines = [
  {
    id: 1,
    sequence: 1,
    component_id: 10,
    component_name: 'Steel Widget',
    component_sku: 'SW-001',
    component_unit: 'EA',
    component_cost: '15.50',
    component_cost_unit: 'EA',
    is_material: false,
    quantity: '2.00',
    unit: 'EA',
    line_cost: '31.00',
    has_bom: false,
  },
]

const baseProps = {
  lines,
  editingLine: null,
  setEditingLine: vi.fn(),
  uoms: [],
  onUpdateLine: vi.fn(),
  onDeleteLine: vi.fn(),
}

const renderWith = (currency, locale = 'en-US') =>
  render(
    <MockLocaleProvider currency={currency} locale={locale}>
      <BOMLinesList {...baseProps} />
    </MockLocaleProvider>
  )

describe('BOMLinesList — currency display', () => {
  it('shows $ with USD for component_cost', () => {
    renderWith('USD')
    // component_cost renders as "$15.50/EA"
    expect(screen.getByText(/\$15\.50/)).toBeInTheDocument()
  })

  it('shows € instead of $ with EUR for component_cost', () => {
    renderWith('EUR')
    expect(screen.getByText(/€15\.50/)).toBeInTheDocument()
    expect(screen.queryByText(/\$15\.50/)).not.toBeInTheDocument()
  })

  it('shows £ instead of $ with GBP for component_cost', () => {
    renderWith('GBP')
    expect(screen.getByText(/£15\.50/)).toBeInTheDocument()
    expect(screen.queryByText(/\$15\.50/)).not.toBeInTheDocument()
  })

  it('shows $ with USD for line_cost', () => {
    renderWith('USD')
    expect(screen.getByText('$31.00')).toBeInTheDocument()
  })

  it('shows € instead of $ with EUR for line_cost', () => {
    renderWith('EUR')
    expect(screen.getByText('€31.00')).toBeInTheDocument()
    expect(screen.queryByText('$31.00')).not.toBeInTheDocument()
  })
})
