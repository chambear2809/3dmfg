import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import CurrencyField from '../CurrencyField'

describe('CurrencyField', () => {
  it('renders an input element', () => {
    render(<CurrencyField id="price" value="" onChange={() => {}} />)
    const input = screen.getByRole('textbox')
    expect(input).toBeInTheDocument()
    expect(input).toHaveAttribute('inputMode', 'decimal')
  })

  it('displays the provided value', () => {
    render(<CurrencyField id="price" value="12.50" onChange={() => {}} />)
    expect(screen.getByRole('textbox')).toHaveValue('12.50')
  })

  it('displays empty string when value is null', () => {
    render(<CurrencyField id="price" value={null} onChange={() => {}} />)
    expect(screen.getByRole('textbox')).toHaveValue('')
  })

  it('calls onChange with parsed decimal on input', () => {
    const handleChange = vi.fn()
    render(<CurrencyField id="price" value="" onChange={handleChange} />)
    fireEvent.change(screen.getByRole('textbox'), { target: { value: '25.99' } })
    expect(handleChange).toHaveBeenCalledWith(25.99)
  })

  it('calls onChange with empty string for non-numeric input', () => {
    const handleChange = vi.fn()
    render(<CurrencyField id="price" value="10" onChange={handleChange} />)
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'abc' } })
    expect(handleChange).toHaveBeenCalledWith('')
  })

  it('shows error message when error prop is provided', () => {
    render(<CurrencyField id="price" value="" onChange={() => {}} error="Required field" />)
    const errorMsg = screen.getByRole('alert')
    expect(errorMsg).toBeInTheDocument()
    expect(errorMsg).toHaveTextContent('Required field')
  })

  it('sets aria-invalid when error is present', () => {
    render(<CurrencyField id="price" value="" onChange={() => {}} error="Bad value" />)
    expect(screen.getByRole('textbox')).toHaveAttribute('aria-invalid', 'true')
  })

  it('sets aria-describedby linking input to error message', () => {
    render(<CurrencyField id="cost" value="" onChange={() => {}} error="Too high" />)
    const input = screen.getByRole('textbox')
    expect(input).toHaveAttribute('aria-describedby', 'cost-error')
    expect(screen.getByRole('alert')).toHaveAttribute('id', 'cost-error')
  })

  it('does not show error message when error prop is absent', () => {
    render(<CurrencyField id="price" value="10" onChange={() => {}} />)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('does not set aria-invalid when no error', () => {
    render(<CurrencyField id="price" value="10" onChange={() => {}} />)
    expect(screen.getByRole('textbox')).not.toHaveAttribute('aria-invalid')
  })

  it('formats value on blur when valid number', () => {
    render(<CurrencyField id="price" value="1234.5" onChange={() => {}} />)
    const input = screen.getByRole('textbox')
    fireEvent.blur(input)
    // After blur, the input value should be formatted as currency
    expect(input.value).toMatch(/\$1,234\.50/)
  })
})
