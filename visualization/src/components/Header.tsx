import {
  eraData,
  eraColors,
  eraOrder,
  changeTypeConfig,
  type Era,
} from '../utils/uxSettings';

interface HeaderProps {
  selectedEra: Era | null;
  setSelectedEra: (era: Era | null) => void;
}

export function Header({ selectedEra, setSelectedEra }: HeaderProps) {
  return (
    <>
      {/* Top row: Title + Attribution */}
      <div className="header-top">
        <div className="header-title-group">
          <h1 className="header-title">
            15 Years of StarCraft II{' '}
            <a
              href="https://www.youtube.com/watch?v=pw_GN3v-0Ls"
              target="_blank"
              rel="noopener noreferrer"
              className="balance-easter-egg"
              style={{ '--balance-color': changeTypeConfig.mixed.color } as React.CSSProperties}
            >
              <span className="balance-text">Balance Changes</span>
            </a>
            {' '}Visualized
          </h1>
        </div>
        <div className="attribution">
          <span className="attribution-author">by <a href="https://p.migdal.pl" target="_blank" rel="noopener noreferrer">Piotr Migdał</a></span>
          <a href="https://github.com/stared/sc2-balance-timeline" target="_blank" rel="noopener noreferrer" className="attribution-source">source code & about</a>
          <a href="https://news.ycombinator.com/item?id=46567894" target="_blank" rel="noopener noreferrer" className="attribution-source">discuss on Hacker News</a>
        </div>
      </div>

      {/* Era Timeline */}
      <div className="era-timeline">
        {eraOrder.map((era, i) => (
          <button
            key={era}
            className={`timeline-segment ${selectedEra === era ? 'active' : ''} ${selectedEra && selectedEra !== era ? 'inactive' : ''}`}
            style={{ '--segment-color': eraColors[era] } as React.CSSProperties}
            onClick={() => setSelectedEra(selectedEra === era ? null : era)}
            title={`${eraData[era].name} (${eraData[era].version})`}
          >
            <div className="segment-label">{eraData[era].short}</div>
            <div className="segment-track">
              <div className="segment-line" />
            </div>
            <div className="segment-date">{eraData[era].releaseDate}{i === eraOrder.length - 1 && <span className="segment-date-now">now</span>}</div>
          </button>
        ))}
      </div>
    </>
  );
}
