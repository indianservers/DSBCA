import 'package:flutter/material.dart';

abstract final class DSBColors {
  static const background = Color(0xFFF6F3FC);
  static const navy = Color(0xFF171337);
  static const violet = Color(0xFF7132F5);
  static const lavender = Color(0xFFEEE6FF);
  static const border = Color(0xFFE4DDF4);
  static const text = Color(0xFF24212D);
  static const muted = Color(0xFF665F73);
  static const peach = Color(0xFFFFE3D8);
}

abstract final class DSBSpacing {
  static const page = 20.0;
  static const card = 16.0;
  static const gap = 12.0;
}

abstract final class DSBTypography {
  static const heading = TextStyle(
    fontFamily: 'packages/design_system/DSBSerif',
    fontFamilyFallback: ['Times New Roman'],
    fontSize: 28,
    fontWeight: FontWeight.w700,
    height: 1.15,
  );
  static const muted = TextStyle(
    color: DSBColors.muted,
    fontSize: 13,
    height: 1.4,
  );
}

abstract final class DSBTheme {
  static ThemeData get light => ThemeData(
    useMaterial3: true,
    scaffoldBackgroundColor: DSBColors.background,
    fontFamily: 'packages/design_system/DSBBody',
    colorScheme: ColorScheme.fromSeed(
      seedColor: DSBColors.violet,
      primary: DSBColors.violet,
      surface: Colors.white,
      onSurface: DSBColors.text,
    ),
    textTheme: const TextTheme(
      bodyMedium: TextStyle(fontSize: 14, height: 1.4, color: DSBColors.text),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: const Color(0xFFFAF8FF),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 15),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: DSBColors.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: DSBColors.border, width: 1.5),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: DSBColors.violet,
        foregroundColor: Colors.white,
        minimumSize: const Size(44, 50),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        textStyle: const TextStyle(
          fontFamily: 'packages/design_system/DSBBody',
          fontSize: 14,
          fontWeight: FontWeight.w700,
        ),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        minimumSize: const Size(44, 48),
        side: const BorderSide(color: DSBColors.border, width: 1.5),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      ),
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: DSBColors.background,
      scrolledUnderElevation: 0,
    ),
    dividerColor: DSBColors.border,
  );
}

class DSBPrimaryButton extends StatelessWidget {
  const DSBPrimaryButton(
    this.label, {
    super.key,
    this.onPressed,
    this.loading = false,
  });
  final String label;
  final VoidCallback? onPressed;
  final bool loading;
  @override
  Widget build(BuildContext context) => FilledButton(
    onPressed: loading ? null : onPressed,
    child: loading
        ? const SizedBox(
            width: 20,
            height: 20,
            child: CircularProgressIndicator(strokeWidth: 2),
          )
        : Text(label),
  );
}

class DSBSecondaryButton extends StatelessWidget {
  const DSBSecondaryButton(this.label, {super.key, this.onPressed});
  final String label;
  final VoidCallback? onPressed;
  @override
  Widget build(BuildContext context) =>
      OutlinedButton(onPressed: onPressed, child: Text(label));
}

class DSBTextField extends StatelessWidget {
  const DSBTextField({
    super.key,
    this.controller,
    this.label,
    this.hint,
    this.obscure = false,
    this.keyboardType,
    this.onChanged,
  });
  final TextEditingController? controller;
  final String? label, hint;
  final bool obscure;
  final TextInputType? keyboardType;
  final ValueChanged<String>? onChanged;
  @override
  Widget build(BuildContext context) => TextField(
    controller: controller,
    obscureText: obscure,
    keyboardType: keyboardType,
    onChanged: onChanged,
    decoration: InputDecoration(labelText: label, hintText: hint),
  );
}

class DSBSearchBar extends StatelessWidget {
  const DSBSearchBar({
    super.key,
    required this.hint,
    this.onChanged,
    this.onSubmitted,
  });
  final String hint;
  final ValueChanged<String>? onChanged, onSubmitted;
  @override
  Widget build(BuildContext context) => TextField(
    onChanged: onChanged,
    onSubmitted: onSubmitted,
    decoration: InputDecoration(
      hintText: hint,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      prefixIcon: const Icon(Icons.search, color: DSBColors.violet, size: 21),
      isDense: true,
    ),
  );
}

class DSBCard extends StatelessWidget {
  const DSBCard({
    super.key,
    required this.child,
    this.color = Colors.white,
    this.padding = 16,
    this.outlined = false,
  });
  final Widget child;
  final Color color;
  final double padding;
  final bool outlined;
  @override
  Widget build(BuildContext context) => Container(
    padding: EdgeInsets.all(padding),
    decoration: BoxDecoration(
      color: color,
      borderRadius: BorderRadius.circular(20),
      border: outlined ? Border.all(color: DSBColors.border) : null,
    ),
    child: child,
  );
}

class DSBCategoryChip extends StatelessWidget {
  const DSBCategoryChip(
    this.label, {
    super.key,
    this.selected = false,
    this.onTap,
    this.multi = false,
  });
  final String label;
  final bool selected, multi;
  final VoidCallback? onTap;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(right: 8),
    child: ActionChip(
      onPressed: onTap,
      backgroundColor: selected
          ? (multi ? DSBColors.violet : DSBColors.navy)
          : Colors.white,
      side: BorderSide(color: selected ? Colors.transparent : DSBColors.border),
      shape: const StadiumBorder(),
      label: Text(
        label,
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w700,
          color: selected ? Colors.white : DSBColors.text,
        ),
      ),
    ),
  );
}

class DSBBottomNavigation extends StatelessWidget {
  const DSBBottomNavigation({
    super.key,
    required this.index,
    required this.onTap,
  });
  final int index;
  final ValueChanged<int> onTap;
  static const labels = ['Home', 'Discuss', 'Learn', 'Toolkit', 'Updates'];
  static const icons = [
    Icons.home_outlined,
    Icons.chat_bubble_outline,
    Icons.ondemand_video_outlined,
    Icons.calculate_outlined,
    Icons.notifications_none,
  ];
  @override
  Widget build(BuildContext context) => Container(
    decoration: const BoxDecoration(
      color: Colors.white,
      border: Border(top: BorderSide(color: DSBColors.border)),
    ),
    child: SafeArea(
      top: false,
      child: SizedBox(
        height: 78,
        child: Row(
          children: List.generate(
            5,
            (i) => Expanded(
              child: InkWell(
                onTap: () => onTap(i),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      icons[i],
                      color: i == index ? DSBColors.violet : DSBColors.muted,
                    ),
                    const SizedBox(height: 5),
                    Text(
                      labels[i],
                      style: TextStyle(
                        fontSize: 12,
                        color: i == index ? DSBColors.violet : DSBColors.muted,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    ),
  );
}

class DSBVideoCard extends StatelessWidget {
  const DSBVideoCard({
    super.key,
    required this.title,
    required this.index,
    this.duration = '—',
    this.onTap,
    this.demo = false,
  });
  final String title, duration;
  final int index;
  final VoidCallback? onTap;
  final bool demo;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 10),
    child: InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(18),
      child: DSBCard(
        padding: 8,
        child: Row(
          children: [
            Container(
              width: 120,
              height: 74,
              decoration: BoxDecoration(
                color: Color.lerp(
                  DSBColors.navy,
                  DSBColors.violet,
                  (index % 4) * .13,
                ),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Stack(
                children: [
                  Positioned(
                    left: 8,
                    top: 4,
                    child: Text(
                      '$index',
                      style: const TextStyle(
                        color: Color(0xFFB69AFF),
                        fontSize: 22,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  const Center(
                    child: Icon(
                      Icons.play_circle_fill,
                      color: Colors.white,
                      size: 30,
                    ),
                  ),
                  Positioned(
                    right: 5,
                    bottom: 5,
                    child: Container(
                      color: DSBColors.navy,
                      child: Text(
                        duration,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 11,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${demo ? "Demo · " : ""}DSB Chartered Accountants',
                    style: DSBTypography.muted,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    ),
  );
}

class DSBPublicationCard extends StatelessWidget {
  const DSBPublicationCard({
    super.key,
    required this.title,
    this.subtitle = '',
    this.onTap,
  });
  final String title, subtitle;
  final VoidCallback? onTap;
  @override
  Widget build(BuildContext context) => InkWell(
    onTap: onTap,
    child: DSBCard(
      outlined: true,
      child: Row(
        children: [
          Container(
            width: 55,
            height: 78,
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: DSBColors.navy,
              borderRadius: BorderRadius.circular(8),
              border: const Border(
                left: BorderSide(color: DSBColors.violet, width: 4),
              ),
            ),
            child: const Text(
              'DSB',
              style: TextStyle(
                color: Color(0xFFB69AFF),
                fontSize: 10,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'BOOK · LIBRARY',
                  style: TextStyle(
                    color: DSBColors.violet,
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  title,
                  style: DSBTypography.heading.copyWith(fontSize: 21),
                ),
                Text(subtitle, style: DSBTypography.muted),
              ],
            ),
          ),
        ],
      ),
    ),
  );
}

class DSBReminderCard extends StatelessWidget {
  const DSBReminderCard({
    super.key,
    required this.title,
    this.subtitle = '',
    this.badge = '',
    this.onTap,
  });
  final String title, subtitle, badge;
  final VoidCallback? onTap;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: InkWell(
      onTap: onTap,
      child: DSBCard(
        padding: 12,
        child: Row(
          children: [
            const Icon(Icons.circle, color: DSBColors.violet, size: 10),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  Text(subtitle, style: DSBTypography.muted),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
              decoration: BoxDecoration(
                color: DSBColors.lavender,
                borderRadius: BorderRadius.circular(20),
              ),
              child: Text(
                badge,
                style: const TextStyle(fontSize: 12, color: DSBColors.violet),
              ),
            ),
          ],
        ),
      ),
    ),
  );
}

class DSBNotificationTile extends StatelessWidget {
  const DSBNotificationTile({
    super.key,
    required this.title,
    required this.body,
    this.category = '',
    this.read = false,
    this.onTap,
  });
  final String title, body, category;
  final bool read;
  final VoidCallback? onTap;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 10),
    child: InkWell(
      onTap: onTap,
      child: DSBCard(
        padding: 14,
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 38,
              height: 40,
              decoration: BoxDecoration(
                color: DSBColors.navy,
                borderRadius: BorderRadius.circular(10),
              ),
              alignment: Alignment.center,
              child: const Text(
                'DSB',
                style: TextStyle(
                  color: Color(0xFFB69AFF),
                  fontSize: 11,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (category.isNotEmpty)
                    Text(
                      category.toUpperCase(),
                      style: const TextStyle(
                        fontSize: 11,
                        color: DSBColors.violet,
                        fontWeight: FontWeight.w700,
                        letterSpacing: .6,
                      ),
                    ),
                  Text(
                    title,
                    style: TextStyle(
                      fontWeight: read ? FontWeight.w500 : FontWeight.w700,
                    ),
                  ),
                  Text(body, style: DSBTypography.muted),
                ],
              ),
            ),
            if (!read)
              const Icon(Icons.circle, color: DSBColors.violet, size: 7),
          ],
        ),
      ),
    ),
  );
}

class DSBCompanySelector extends StatelessWidget {
  const DSBCompanySelector({
    super.key,
    required this.value,
    required this.items,
    required this.onChanged,
  });
  final String? value;
  final Map<String, String> items;
  final ValueChanged<String?> onChanged;
  @override
  Widget build(BuildContext context) => DropdownButtonFormField<String>(
    initialValue: value,
    isExpanded: true,
    decoration: const InputDecoration(
      prefixIcon: Icon(Icons.business_outlined),
    ),
    items: items.entries
        .map(
          (e) => DropdownMenuItem(
            value: e.key,
            child: Text(e.value, overflow: TextOverflow.ellipsis),
          ),
        )
        .toList(),
    onChanged: onChanged,
  );
}

class DSBLoadingState extends StatelessWidget {
  const DSBLoadingState({super.key});
  @override
  Widget build(BuildContext context) => const Padding(
    padding: EdgeInsets.all(32),
    child: Center(child: CircularProgressIndicator()),
  );
}

class DSBEmptyState extends StatelessWidget {
  const DSBEmptyState(this.message, {super.key});
  final String message;
  @override
  Widget build(BuildContext context) => DSBCard(
    child: Padding(
      padding: const EdgeInsets.symmetric(vertical: 16),
      child: Center(
        child: Text(
          message,
          textAlign: TextAlign.center,
          style: DSBTypography.muted,
        ),
      ),
    ),
  );
}

class DSBErrorState extends StatelessWidget {
  const DSBErrorState(this.message, {super.key, this.onRetry});
  final String message;
  final VoidCallback? onRetry;
  @override
  Widget build(BuildContext context) => DSBCard(
    child: Column(
      children: [
        Text(message, style: const TextStyle(color: Color(0xFFAF3010))),
        if (onRetry != null)
          TextButton(onPressed: onRetry, child: const Text('Try again')),
      ],
    ),
  );
}

class DSBDialog extends StatelessWidget {
  const DSBDialog({
    super.key,
    required this.title,
    required this.child,
    this.actions,
  });
  final String title;
  final Widget child;
  final List<Widget>? actions;
  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text(title),
    content: SizedBox(width: 440, child: SingleChildScrollView(child: child)),
    actions: actions,
  );
}
