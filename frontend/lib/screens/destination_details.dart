import 'package:flutter/material.dart';
import '../models/destination.dart';
import '../services/api_client.dart';
import '../widgets/brand.dart';

class DestinationDetails extends StatefulWidget {
  final Destination destination;
  final ApiClient api;
  final VoidCallback onPlan;
  final VoidCallback onInspiration;
  const DestinationDetails({
    super.key,
    required this.destination,
    required this.api,
    required this.onPlan,
    required this.onInspiration,
  });
  @override
  State<DestinationDetails> createState() => _DestinationDetailsState();
}

class _DestinationDetailsState extends State<DestinationDetails> {
  late Future<Map<String, dynamic>> _detail;
  @override
  void initState() {
    super.initState();
    _detail = widget.api.detail(widget.destination.id);
  }

  @override
  Widget build(BuildContext context) => SizedBox(
    height: MediaQuery.sizeOf(context).height * .88,
    child: FutureBuilder<Map<String, dynamic>>(
      future: _detail,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return StatusPanel(
            title: 'Could not load this destination',
            message: '${snapshot.error}',
            onRetry: () => setState(
              () => _detail = widget.api.detail(widget.destination.id),
            ),
          );
        }
        final detail = snapshot.data!;
        return SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      widget.destination.name,
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                  ),
                  IconButton(
                    tooltip: 'Close destination',
                    onPressed: () => Navigator.pop(context),
                    icon: const Icon(Icons.close),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                '${widget.destination.state} · ${widget.destination.region}',
              ),
              const SizedBox(height: 20),
              ClipRRect(
                borderRadius: BorderRadius.circular(18),
                child: SizedBox(
                  height: 180,
                  child: Landscape(interests: widget.destination.interests),
                ),
              ),
              const SizedBox(height: 20),
              Text(
                widget.destination.description,
                style: const TextStyle(height: 1.6),
              ),
              const SizedBox(height: 20),
              Text(
                'Worth exploring',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              ...widget.destination.attractions.map(
                (a) => ListTile(
                  contentPadding: EdgeInsets.zero,
                  dense: true,
                  leading: const Icon(Icons.place_outlined, color: teal),
                  title: Text(a),
                ),
              ),
              const SizedBox(height: 12),
              Text(
                'Good to know',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              Text(
                'Best seasons: ${widget.destination.seasons.join(', ')}\nAvoid: ${(detail['avoid_seasons'] as List).join(', ')}\n\n${detail['special_considerations']}\n\nPermits: ${detail['permits_details']}\n\n${detail['safety_notes']}',
                style: const TextStyle(height: 1.6),
              ),
              const SizedBox(height: 18),
              Text(
                detail['food_scene'] as String,
                style: const TextStyle(height: 1.6),
              ),
              const SizedBox(height: 24),
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: [
                  FilledButton.icon(
                    onPressed: widget.onPlan,
                    icon: const Icon(Icons.route_outlined),
                    label: const Text('Plan this trip'),
                  ),
                  OutlinedButton(
                    onPressed: widget.onInspiration,
                    child: const Text('Use as inspiration'),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    ),
  );
}
