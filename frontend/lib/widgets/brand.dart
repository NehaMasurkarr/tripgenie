import 'package:flutter/material.dart';

const ink = Color(0xFF153D3A);
const teal = Color(0xFF176D63);
const paper = Color(0xFFF6F5EF);
const coral = Color(0xFFCE714C);

String money(num value) =>
    '₹${value.toStringAsFixed(0).replaceAllMapped(RegExp(r'(\d)(?=(\d{3})+$)'), (m) => '${m[1]},')}';
String label(String value) => value
    .split(' ')
    .map((v) => v.isEmpty ? v : '${v[0].toUpperCase()}${v.substring(1)}')
    .join(' ');

class SectionHeading extends StatelessWidget {
  final String eyebrow;
  final String title;
  final String subtitle;
  const SectionHeading({
    super.key,
    required this.eyebrow,
    required this.title,
    required this.subtitle,
  });
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 24),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          eyebrow.toUpperCase(),
          style: const TextStyle(
            color: teal,
            letterSpacing: 2,
            fontSize: 11,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          title,
          style: Theme.of(context).textTheme.headlineLarge?.copyWith(
            color: ink,
            fontFamily: 'Georgia',
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 10),
        Text(
          subtitle,
          style: const TextStyle(color: Color(0xFF586C65), height: 1.5),
        ),
      ],
    ),
  );
}

class StatusPanel extends StatelessWidget {
  final String title;
  final String message;
  final VoidCallback? onRetry;
  const StatusPanel({
    super.key,
    required this.title,
    required this.message,
    this.onRetry,
  });
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.all(32),
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Icon(Icons.explore_outlined, size: 48, color: teal),
        const SizedBox(height: 16),
        Text(
          title,
          style: Theme.of(context).textTheme.titleLarge,
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 8),
        Text(message, textAlign: TextAlign.center),
        if (onRetry != null)
          Padding(
            padding: const EdgeInsets.only(top: 16),
            child: FilledButton(
              onPressed: onRetry,
              child: const Text('Try again'),
            ),
          ),
      ],
    ),
  );
}

class Landscape extends StatelessWidget {
  final List<String> interests;
  const Landscape({super.key, required this.interests});
  @override
  Widget build(BuildContext context) => CustomPaint(
    painter: _LandscapePainter(
      interests.contains('beach') || interests.contains('island'),
    ),
    child: const SizedBox.expand(),
  );
}

class _LandscapePainter extends CustomPainter {
  final bool coast;
  _LandscapePainter(this.coast);
  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;
    canvas.drawRect(
      rect,
      Paint()
        ..shader = LinearGradient(
          colors: coast
              ? [const Color(0xFFBBDCD7), const Color(0xFFE1EADA)]
              : [const Color(0xFFE5D3B2), const Color(0xFFD2E1C9)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ).createShader(rect),
    );
    canvas.drawCircle(
      Offset(size.width * .78, size.height * .25),
      size.height * .13,
      Paint()..color = const Color(0xFFF9EECD),
    );
    for (var i = 0; i < 3; i++) {
      final path = Path()..moveTo(0, size.height * (.55 + i * .12));
      if (coast) {
        path.cubicTo(
          size.width * .25,
          size.height * (.35 + i * .13),
          size.width * .55,
          size.height * (.75 + i * .05),
          size.width,
          size.height * (.6 + i * .1),
        );
      } else {
        path.lineTo(size.width * .22, size.height * (.2 + i * .2));
        path.lineTo(size.width * .5, size.height * (.6 + i * .05));
        path.lineTo(size.width * .72, size.height * (.3 + i * .17));
        path.lineTo(size.width, size.height * (.56 + i * .1));
      }
      path.lineTo(size.width, size.height);
      path.lineTo(0, size.height);
      path.close();
      canvas.drawPath(
        path,
        Paint()
          ..color = [
            const Color(0xFF81B8A6),
            const Color(0xFF4A8D7E),
            const Color(0xFF25665D),
          ][i],
      );
    }
  }

  @override
  bool shouldRepaint(_LandscapePainter oldDelegate) =>
      oldDelegate.coast != coast;
}
