import 'package:flutter/material.dart';
import '../models/destination.dart';
import '../widgets/brand.dart';

class PreferencesPanel extends StatefulWidget {
  final Map<String, dynamic> options;
  final Destination? inspiration;
  final bool loading;
  final ValueChanged<Map<String, dynamic>> onSubmit;
  final VoidCallback onClearInspiration;
  const PreferencesPanel({
    super.key,
    required this.options,
    this.inspiration,
    required this.loading,
    required this.onSubmit,
    required this.onClearInspiration,
  });
  @override
  State<PreferencesPanel> createState() => _PreferencesPanelState();
}

class _PreferencesPanelState extends State<PreferencesPanel> {
  final _form = GlobalKey<FormState>();
  final _budget = TextEditingController(text: '3000');
  final _interests = <String>{'beach', 'nature'};
  String _season = 'winter';
  String _tier = 'budget';
  String? _state;
  double _days = 3;
  bool _strict = false;
  late Map<String, double> _weights;
  @override
  void initState() {
    super.initState();
    _weights = (widget.options['default_weights'] as Map<String, dynamic>).map(
      (k, v) => MapEntry(k, (v as num).toDouble()),
    );
  }

  @override
  void dispose() {
    _budget.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final interests = List<String>.from(widget.options['interests'] as List);
    const featured = [
      'beach',
      'nature',
      'heritage',
      'adventure',
      'wildlife',
      'food',
      'photography',
      'wellness',
      'spiritual',
      'offbeat',
      'trekking',
      'diving',
    ];
    return Form(
      key: _form,
      child: Card(
        margin: EdgeInsets.zero,
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (widget.inspiration != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 16),
                  child: InputChip(
                    avatar: const Icon(Icons.explore, size: 18),
                    label: Text('Inspired by ${widget.inspiration!.name}'),
                    onDeleted: widget.onClearInspiration,
                  ),
                ),
              Text(
                'What draws you in?',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 6),
              const Text('Choose the experiences you want more of.'),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: featured
                    .where(interests.contains)
                    .map(
                      (t) => FilterChip(
                        label: Text(label(t)),
                        selected: _interests.contains(t),
                        onSelected: widget.loading
                            ? null
                            : (selected) => setState(() {
                                selected
                                    ? _interests.add(t)
                                    : _interests.remove(t);
                              }),
                      ),
                    )
                    .toList(),
              ),
              const SizedBox(height: 24),
              LayoutBuilder(
                builder: (context, size) {
                  final fields = [
                    TextFormField(
                      key: const Key('budgetInput'),
                      controller: _budget,
                      decoration: const InputDecoration(
                        labelText: 'Daily budget (INR)',
                        prefixText: '₹ ',
                        helperText:
                            'Estimated local costs, not transport to the destination',
                      ),
                      keyboardType: TextInputType.number,
                      validator: (value) {
                        final n = double.tryParse(value ?? '');
                        return n == null || !n.isFinite || n < 1 || n > 1000000
                            ? 'Enter a budget between ₹1 and ₹1,000,000'
                            : null;
                      },
                    ),
                    DropdownButtonFormField<String>(
                      initialValue: _tier,
                      isExpanded: true,
                      decoration: const InputDecoration(
                        labelText: 'Travel style',
                      ),
                      items: const [
                        DropdownMenuItem(
                          value: 'budget',
                          child: Text('Budget stays'),
                        ),
                        DropdownMenuItem(
                          value: 'mid-range',
                          child: Text('Mid-range comfort'),
                        ),
                        DropdownMenuItem(
                          value: 'luxury',
                          child: Text('Luxury escapes'),
                        ),
                      ],
                      onChanged: (value) => setState(() => _tier = value!),
                    ),
                    DropdownButtonFormField<String>(
                      initialValue: _season,
                      isExpanded: true,
                      decoration: const InputDecoration(
                        labelText: 'When are you going?',
                      ),
                      items:
                          List<String>.from(widget.options['seasons'] as List)
                              .map(
                                (s) => DropdownMenuItem(
                                  value: s,
                                  child: Text(label(s)),
                                ),
                              )
                              .toList(),
                      onChanged: (v) => setState(() => _season = v!),
                    ),
                    DropdownButtonFormField<String>(
                      initialValue: _state,
                      isExpanded: true,
                      decoration: const InputDecoration(
                        labelText: 'State / location',
                      ),
                      items: [
                        const DropdownMenuItem<String>(
                          value: null,
                          child: Text('Anywhere in India'),
                        ),
                        ...List<String>.from(
                          widget.options['states'] as List,
                        ).map(
                          (s) => DropdownMenuItem(
                            value: s,
                            child: Text(s, overflow: TextOverflow.ellipsis),
                          ),
                        ),
                      ],
                      onChanged: (v) => setState(() => _state = v),
                    ),
                  ];
                  final fieldWidth = size.maxWidth < 650
                      ? size.maxWidth
                      : (size.maxWidth - 20) / 2;
                  return Wrap(
                    spacing: 20,
                    runSpacing: 20,
                    children: fields
                        .map((f) => SizedBox(width: fieldWidth, child: f))
                        .toList(),
                  );
                },
              ),
              const SizedBox(height: 22),
              Text(
                'Time to explore · ${_days.round()} days',
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
              Slider(
                value: _days,
                min: 1,
                max: 14,
                divisions: 13,
                label: '${_days.round()} days',
                onChanged: (v) => setState(() => _days = v),
              ),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Keep my trip within these preferences'),
                subtitle: const Text(
                  'Require a season match, recommended day range, and budget covering the lower daily estimate.',
                ),
                value: _strict,
                onChanged: (v) => setState(() => _strict = v),
              ),
              ExpansionTile(
                tilePadding: EdgeInsets.zero,
                title: const Text('Balance your matches'),
                subtitle: const Text('Adjust what matters most to you.'),
                children: [
                  ..._weights.keys.map((k) {
                    const names = {
                      'content': 'Similar experiences',
                      'popularity': 'Popular places',
                      'interests': 'Your interests',
                      'budget': 'Budget fit',
                      'season': 'Season match',
                      'duration': 'Trip length',
                    };
                    return Row(
                      children: [
                        SizedBox(width: 145, child: Text(names[k] ?? k)),
                        Expanded(
                          child: Slider(
                            value: _weights[k]!,
                            min: 0,
                            max: 1,
                            divisions: 20,
                            label: _weights[k]!.toStringAsFixed(2),
                            onChanged: (v) => setState(() => _weights[k] = v),
                          ),
                        ),
                      ],
                    );
                  }),
                ],
              ),
              const SizedBox(height: 18),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  key: const Key('recommendButton'),
                  onPressed: widget.loading
                      ? null
                      : () {
                          if (!_form.currentState!.validate()) {
                            return;
                          }
                          if (_weights.values.every((v) => v == 0)) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content: Text(
                                  'Give at least one match factor a positive weight.',
                                ),
                              ),
                            );
                            return;
                          }
                          widget.onSubmit({
                            'interests': _interests.toList(),
                            'daily_budget': double.parse(_budget.text),
                            'budget_tier': _tier,
                            'season': _season,
                            'trip_days': _days.round(),
                            'strict_filters': _strict,
                            'weights': Map<String, double>.from(_weights),
                            if (_state != null) 'state': _state,
                            if (widget.inspiration != null)
                              'selected_destination': widget.inspiration!.id,
                          });
                        },
                  icon: widget.loading
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.auto_awesome),
                  label: Text(
                    widget.loading
                        ? 'Finding your matches…'
                        : 'Find my destinations',
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
