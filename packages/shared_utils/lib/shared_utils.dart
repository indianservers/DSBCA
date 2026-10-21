class GratuityResult {
  const GratuityResult(this.firstFive, this.laterYears, this.total);
  final double firstFive, laterYears, total;
}

GratuityResult calculateGratuity(double monthlyBasic, double years) {
  if (!monthlyBasic.isFinite ||
      !years.isFinite ||
      monthlyBasic <= 0 ||
      years < 0 ||
      years > 80) {
    throw ArgumentError(
      'Enter a positive basic salary and service from 0 to 80 years.',
    );
  }
  if (years < 1) return const GratuityResult(0, 0, 0);
  final first = monthlyBasic / 30 * 21 * (years > 5 ? 5 : years);
  final later = monthlyBasic * (years > 5 ? years - 5 : 0);
  final capped = (first + later).clamp(0, monthlyBasic * 24).toDouble();
  return GratuityResult(first, later, (capped * 100).round() / 100);
}

String money(num value) {
  final parts = value.toStringAsFixed(2).split('.');
  final whole = parts.first.replaceAllMapped(
    RegExp(r'(\d)(?=(\d{3})+(?!\d))'),
    (m) => '${m[1]},',
  );
  return parts[1] == '00' ? whole : '$whole.${parts[1]}';
}
