import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { ProcessedPatchData, ViewMode, Unit } from '../types';
import { groupUnitsByRace } from '../utils/dataLoader';

interface PatchGridProps {
  patches: ProcessedPatchData[];
  units: Map<string, Unit>;
  viewMode: ViewMode;
}

export function PatchGrid({ patches, units, viewMode }: PatchGridProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [tooltip, setTooltip] = useState<{
    x: number;
    y: number;
    unit: string;
    changes: string[];
    visible: boolean;
  }>({ x: 0, y: 0, unit: '', changes: [], visible: false });

  useEffect(() => {
    if (!svgRef.current || patches.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    // Get all units that have changes
    const allChangedUnits = new Set<string>();
    patches.forEach(patch => {
      patch.entities.forEach((_, entityId) => {
        allChangedUnits.add(entityId);
      });
    });

    const unitsByRace = groupUnitsByRace(allChangedUnits, units);
    const allUnits = [...unitsByRace.terran, ...unitsByRace.zerg, ...unitsByRace.protoss];  // Fixed order

    const margin = { top: 80, right: 20, bottom: 20, left: 120 };
    const cellSize = 54;
    const cellPadding = 3;

    // For compact view, calculate actual positions based on changes per patch
    let maxUnitsInPatch = 0;
    if (viewMode === 'by-patch') {
      // Calculate max units in any patch for width
      patches.forEach(patch => {
        let unitCount = 0;
        patch.entities.forEach(entity => {
          if (entity.type === 'unit') unitCount++;
        });
        maxUnitsInPatch = Math.max(maxUnitsInPatch, unitCount);
      });

      // Width includes unit section + space + upgrade columns (4 races * 150px each)
      const width = margin.left + margin.right + Math.max(maxUnitsInPatch, 10) * cellSize + 50 + (4 * 150);
      const height = margin.top + margin.bottom + patches.length * cellSize;

      svg.attr('width', width).attr('height', height);
    } else {
      const width = margin.left + margin.right + allUnits.length * cellSize;
      const height = margin.top + margin.bottom + patches.length * cellSize;

      svg.attr('width', width).attr('height', height);
    }

    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    // Create scales
    const xScale = d3.scaleBand()
      .domain(allUnits)
      .range([0, allUnits.length * cellSize])
      .padding(0);

    const yScale = d3.scaleBand()
      .domain(patches.map(p => p.version))
      .range([0, patches.length * cellSize])
      .padding(0);

    // Add race headers (corrected order)
    const raceHeaders = [
      { race: 'terran', units: unitsByRace.terran, color: '#4a9eff' },
      { race: 'zerg', units: unitsByRace.zerg, color: '#c874e9' },      // Zerg second
      { race: 'protoss', units: unitsByRace.protoss, color: '#ffd700' }  // Protoss third
    ];

    let xOffset = 0;
    raceHeaders.forEach(({ race, units: raceUnits, color }) => {
      if (raceUnits.length > 0) {
        g.append('text')
          .attr('x', xOffset + (raceUnits.length * cellSize) / 2)
          .attr('y', -40)
          .attr('text-anchor', 'middle')
          .attr('fill', color)
          .attr('font-size', 16)
          .attr('font-weight', 'bold')
          .text(race.charAt(0).toUpperCase() + race.slice(1));

        xOffset += raceUnits.length * cellSize;
      }
    });

    // Add clickable patch version labels
    const patchLinks = g.append('g')
      .selectAll('a')
      .data(patches)
      .enter()
      .append('a')
      .attr('href', d => d.url)
      .attr('target', '_blank')
      .attr('rel', 'noopener noreferrer');

    patchLinks.append('text')
      .attr('x', -10)
      .attr('y', (d) => yScale(d.version)! + cellSize / 2)
      .attr('text-anchor', 'end')
      .attr('fill', '#4a9eff')
      .attr('font-size', 12)
      .attr('dominant-baseline', 'middle')
      .style('cursor', 'pointer')
      .style('text-decoration', 'underline')
      .text(d => d.version)
      .on('mouseenter', function() {
        d3.select(this).attr('fill', '#6ab7ff');
      })
      .on('mouseleave', function() {
        d3.select(this).attr('fill', '#4a9eff');
      });

    // Add patch dates
    g.append('g')
      .selectAll('text')
      .data(patches)
      .enter()
      .append('text')
      .attr('x', -60)
      .attr('y', (d) => yScale(d.version)! + cellSize / 2)
      .attr('text-anchor', 'end')
      .attr('fill', '#666')
      .attr('font-size', 10)
      .attr('dominant-baseline', 'middle')
      .text(d => d.date.split('-').slice(0, 2).join('-'));

    // Separate units from other changes (upgrades, buildings, etc.)
    const unitCells: any[] = [];
    const upgradeCells: any[] = [];

    if (viewMode === 'by-patch') {
      // Compact view: only show units that have changes, pack them left to right
      patches.forEach(patch => {
        let unitIndex = 0;
        const upgradesByRace = { terran: [], zerg: [], protoss: [], neutral: [] } as any;

        patch.entities.forEach((entity, entityId) => {
          if (entity.type === 'unit') {
            unitCells.push({
              patch: patch.version,
              patchDate: patch.date,
              entityId,
              entity,
              x: unitIndex * cellSize,
              y: yScale(patch.version)!
            });
            unitIndex++;
          } else {
            // Collect upgrades/buildings/abilities by race
            const race = entity.race as keyof typeof upgradesByRace || 'neutral';
            upgradesByRace[race].push({
              patch: patch.version,
              patchDate: patch.date,
              entityId,
              entity,
              race
            });
          }
        });

        // Add upgrade cells grouped by race
        Object.entries(upgradesByRace).forEach(([race, items]: [string, any[]]) => {
          items.forEach(item => {
            upgradeCells.push(item);
          });
        });
      });
    } else {
      // Full grid view: show all positions for units only
      patches.forEach(patch => {
        patch.entities.forEach((entity, entityId) => {
          if (entity.type === 'unit' && xScale(entityId) !== undefined) {
            unitCells.push({
              patch: patch.version,
              patchDate: patch.date,
              entityId,
              entity,
              x: xScale(entityId)!,
              y: yScale(patch.version)!
            });
          }
        });
      });
    }

    // Render unit cells with images
    const cells = g.append('g')
      .selectAll('g')
      .data(unitCells)
      .enter()
      .append('g')
      .attr('transform', d => `translate(${d.x},${d.y})`);

    // Add unit images
    cells.append('image')
      .attr('x', cellPadding)
      .attr('y', cellPadding)
      .attr('width', cellSize - cellPadding * 2)
      .attr('height', cellSize - cellPadding * 2)
      .attr('href', d => `/assets/units/${d.entityId}.png`)
      .attr('preserveAspectRatio', 'xMidYMid meet')
      .style('cursor', 'pointer')
      .on('error', function() {
        // Fallback to placeholder
        d3.select(this).attr('href', '/assets/units/placeholder.svg');
      })
      .on('mouseenter', function(event, d) {
        const [x, y] = d3.pointer(event, document.body);
        setTooltip({
          x,
          y,
          unit: units.get(d.entityId)?.name || d.entityId,
          changes: d.entity.changes,
          visible: true
        });
      })
      .on('mouseleave', () => {
        setTooltip(prev => ({ ...prev, visible: false }));
      });

    // Add upgrade/building/ability display section
    if (upgradeCells.length > 0) {
      const upgradeSection = svg.append('g')
        .attr('transform', `translate(${margin.left + (maxUnitsInPatch || 10) * cellSize + 50}, ${margin.top})`);

      // Add headers for race columns
      const raceOrder = ['terran', 'zerg', 'protoss', 'neutral'];
      const columnWidth = 150;

      raceOrder.forEach((race, index) => {
        upgradeSection.append('text')
          .attr('x', index * columnWidth + columnWidth / 2)
          .attr('y', -20)
          .attr('text-anchor', 'middle')
          .attr('fill', race === 'terran' ? '#4a9eff' : race === 'zerg' ? '#c874e9' : race === 'protoss' ? '#ffd700' : '#888')
          .attr('font-size', 14)
          .attr('font-weight', 'bold')
          .text(race.charAt(0).toUpperCase() + race.slice(1));
      });

      // Group upgrades by patch and race
      const upgradesByPatchAndRace = new Map<string, Map<string, any[]>>();

      upgradeCells.forEach(cell => {
        if (!upgradesByPatchAndRace.has(cell.patch)) {
          upgradesByPatchAndRace.set(cell.patch, new Map());
        }
        const patchMap = upgradesByPatchAndRace.get(cell.patch)!;

        if (!patchMap.has(cell.race)) {
          patchMap.set(cell.race, []);
        }
        patchMap.get(cell.race)!.push(cell);
      });

      // Render upgrade text in columns
      patches.forEach(patch => {
        const patchUpgrades = upgradesByPatchAndRace.get(patch.version);
        if (patchUpgrades) {
          const y = yScale(patch.version)!;

          raceOrder.forEach((race, raceIndex) => {
            const raceUpgrades = patchUpgrades.get(race) || [];

            raceUpgrades.forEach((upgrade, upgradeIndex) => {
              const textGroup = upgradeSection.append('g')
                .attr('transform', `translate(${raceIndex * columnWidth}, ${y + upgradeIndex * 20})`);

              // Add wrapped text for upgrade name and changes
              const text = textGroup.append('text')
                .attr('font-size', 11)
                .attr('fill', '#ccc');

              // Wrap text to fit in column
              const words = (upgrade.entity.name + ': ' + upgrade.entity.changes[0]).split(' ');
              let line = '';
              let lineNumber = 0;
              const lineHeight = 12;
              const maxWidth = columnWidth - 10;

              words.forEach(word => {
                const testLine = line + word + ' ';
                const testWidth = testLine.length * 6; // Approximate width

                if (testWidth > maxWidth && line !== '') {
                  text.append('tspan')
                    .attr('x', 0)
                    .attr('y', lineNumber * lineHeight)
                    .text(line.trim());
                  line = word + ' ';
                  lineNumber++;

                  if (lineNumber >= 2) return; // Max 2 lines
                } else {
                  line = testLine;
                }
              });

              if (line !== '' && lineNumber < 2) {
                text.append('tspan')
                  .attr('x', 0)
                  .attr('y', lineNumber * lineHeight)
                  .text(line.trim());
              }
            });
          });
        }
      });
    }

    // Add transitions for view mode changes
    if (viewMode === 'by-unit') {
      // Group by unit instead of patch
      const unitGroups = new Map<string, { patches: string[], changes: string[][] }>();

      patches.forEach(patch => {
        patch.entities.forEach((entity, entityId) => {
          if (!unitGroups.has(entityId)) {
            unitGroups.set(entityId, { patches: [], changes: [] });
          }
          const group = unitGroups.get(entityId)!;
          group.patches.push(patch.version);
          group.changes.push(entity.changes);
        });
      });

      // Reorganize the visualization
      // This is a placeholder for the by-unit view transformation
      // You would implement the actual regrouping logic here
    }

  }, [patches, units, viewMode]);

  return (
    <>
      <svg ref={svgRef}></svg>
      {tooltip.visible && (
        <div
          className="tooltip"
          style={{
            left: tooltip.x + 10,
            top: tooltip.y - 10
          }}
        >
          <h4>{tooltip.unit}</h4>
          <ul>
            {tooltip.changes.map((change, i) => (
              <li key={i}>{change}</li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}