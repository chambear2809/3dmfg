import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import PricingStep from '../PricingStep'
import { MockLocaleProvider } from '../../../test/mockLocaleProvider'

const baseProps = {
  item: {
    standard_cost: null,
    selling_price: null,
  },
  calculatedCost: 12.50,
  laborCost: 5.00,
  totalCost: 17.50,
  targetMargin: 30,
  suggestedPrice: 25.00,
  onItemChange: vi.fn(),
  onTargetMarginChange: vi.fn(),
}

const renderWith = (currency, locale = 'en-US') =>
  render(
    <MockLocaleProvider currency={currency} locale={locale}>
      <PricingStep {...baseProps} />
    </MockLocaleProvider>
  )

describe('PricingStep — currency display', () => {
  it('shows $ with USD for totalCost', () => {
    renderWith('USD')
    expect(screen.getByText('$17.50')).toBeInTheDocument()
  })

  it('shows € instead of $ with EUR for totalCost', () => {
    renderWith('EUR')
    expect(screen.getByText('€17.50')).toBeInTheDocument()
    expect(screen.queryByText('$17.50')).not.toBeInTheDocument()
  })

  it('shows £ instead of $ with GBP for totalCost', () => {
    renderWith('GBP')
    expect(screen.getByText('£17.50')).toBeInTheDocument()
    expect(screen.queryByText('$17.50')).not.toBeInTheDocument()
  })

  it('shows $ with USD for suggestedPrice button', () => {
    renderWith('USD')
    expect(screen.getByText('$25.00')).toBeInTheDocument()
  })

  it('shows € instead of $ with EUR for suggestedPrice button', () => {
    renderWith('EUR')
    expect(screen.getByText('€25.00')).toBeInTheDocument()
    expect(screen.queryByText('$25.00')).not.toBeInTheDocument()
  })

  it('shows $ with USD for calculatedCost (Material Cost row)', () => {
    renderWith('USD')
    expect(screen.getByText('$12.50')).toBeInTheDocument()
  })

  it('shows € instead of $ with EUR for calculatedCost (Material Cost row)', () => {
    renderWith('EUR')
    expect(screen.getByText('€12.50')).toBeInTheDocument()
    expect(screen.queryByText('$12.50')).not.toBeInTheDocument()
  })
})
