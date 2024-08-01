def float_to_string(number, precision=40):
  if number is None:
    return 'None'
  try:
    return '{0:.{prec}f}'.format(number, prec=precision,).rstrip('0').rstrip('.') or '0'
  except Exception as e:
    return 'NaN'

