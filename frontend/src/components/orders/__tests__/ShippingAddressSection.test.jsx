import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import ShippingAddressSection from '../ShippingAddressSection'
import { ToastProvider } from '../../Toast'

const order = {
  id: 7,
  shipping_address_line1: '123 Main St',
  shipping_address_line2: 'Suite 400',
  shipping_city: 'Boston',
  shipping_state: 'MA',
  shipping_zip: '02110',
  shipping_country: 'USA',
}

describe('ShippingAddressSection replay privacy', () => {
  it('masks rendered address values but leaves section chrome visible', () => {
    render(
      <ToastProvider>
        <ShippingAddressSection order={order} onOrderUpdated={vi.fn()} />
      </ToastProvider>
    )

    expect(screen.getByText('Shipping Address').closest('[data-rum-mask="true"]')).toBeNull()
    expect(screen.getByText('Edit').closest('[data-rum-mask="true"]')).toBeNull()

    const addressLine = screen.getByText('123 Main St')
    expect(addressLine.closest('[data-rum-mask="true"]')).toHaveAttribute('data-rum-mask', 'true')

    const cityLine = screen.getByText(/Boston, MA 02110/)
    expect(cityLine.closest('[data-rum-mask="true"]')).toHaveAttribute('data-rum-mask', 'true')
  })
})
