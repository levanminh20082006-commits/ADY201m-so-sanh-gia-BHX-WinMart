/* ADY201m Report 2 - SQL Server schema (run inside the approved database, e.g. ADY201m_Report2).
   Safe to run many times: every object is created only if it does not exist yet.

   Stores (1) ──< Products (N) ──< PriceObservations (N) >── (1) CollectionRuns
   ProductMatches links one BHX product with one WinMart product for a run.
*/

IF OBJECT_ID('dbo.Stores', 'U') IS NULL
CREATE TABLE dbo.Stores (
    store_code   varchar(10)   NOT NULL CONSTRAINT PK_Stores PRIMARY KEY,   -- 'bhx' / 'winmart'
    store_name   nvarchar(100) NOT NULL,
    website      varchar(200)  NOT NULL
);
GO

IF OBJECT_ID('dbo.CollectionRuns', 'U') IS NULL
CREATE TABLE dbo.CollectionRuns (
    run_id       varchar(40)       NOT NULL CONSTRAINT PK_CollectionRuns PRIMARY KEY,
    started_at   datetimeoffset(0) NOT NULL,           -- Vietnam time, +07:00
    finished_at  datetimeoffset(0) NULL,
    pages_total  int               NOT NULL CONSTRAINT CK_Runs_Pages CHECK (pages_total >= 0),
    pages_ok     int               NOT NULL,
    raw_folder   nvarchar(300)     NOT NULL,           -- where the raw JSON evidence is kept
    loaded_at    datetimeoffset(0) NOT NULL CONSTRAINT DF_Runs_Loaded DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT CK_Runs_OkPages CHECK (pages_ok BETWEEN 0 AND pages_total)
);
GO

IF OBJECT_ID('dbo.Products', 'U') IS NULL
CREATE TABLE dbo.Products (
    product_key        int IDENTITY(1,1) NOT NULL CONSTRAINT PK_Products PRIMARY KEY,
    store_code         varchar(10)    NOT NULL CONSTRAINT FK_Products_Stores REFERENCES dbo.Stores(store_code),
    store_product_code varchar(50)    NOT NULL,        -- BHX productCode / WinMart itemNo
    barcode            varchar(20)    NULL,            -- only WinMart publishes it
    name               nvarchar(400)  NOT NULL,
    brand              nvarchar(100)  NULL,
    size_value         decimal(12,3)  NULL CONSTRAINT CK_Products_Size CHECK (size_value IS NULL OR size_value > 0),
    size_unit          varchar(5)     NULL CONSTRAINT CK_Products_Unit CHECK (size_unit IN ('g', 'ml')),
    pack_count         int            NULL CONSTRAINT CK_Products_Pack CHECK (pack_count IS NULL OR pack_count > 0),
    unit_label         nvarchar(50)   NULL,            -- 'Hộp', 'Lốc', 'Thùng' ...
    product_url        nvarchar(500)  NOT NULL,
    first_seen_run     varchar(40)    NOT NULL,
    last_seen_run      varchar(40)    NOT NULL,
    CONSTRAINT UQ_Products_StoreCode UNIQUE (store_code, store_product_code)   -- no duplicate products
);
GO

IF OBJECT_ID('dbo.PriceObservations', 'U') IS NULL
CREATE TABLE dbo.PriceObservations (
    observation_id       char(20)          NOT NULL CONSTRAINT PK_PriceObservations PRIMARY KEY,
    run_id               varchar(40)       NOT NULL CONSTRAINT FK_Obs_Runs REFERENCES dbo.CollectionRuns(run_id),
    product_key          int               NOT NULL CONSTRAINT FK_Obs_Products REFERENCES dbo.Products(product_key),
    collected_at         datetimeoffset(0) NOT NULL,
    category_slug        varchar(100)      NOT NULL,
    sale_price_vnd       decimal(12,0)     NOT NULL CONSTRAINT CK_Obs_Price CHECK (sale_price_vnd > 0),
    list_price_vnd       decimal(12,0)     NULL,
    is_promotion         bit               NOT NULL,
    flash_sale_price_vnd decimal(12,0)     NULL,       -- BHX time-limited price, kept separately
    price_store_id       varchar(20)       NULL,       -- store the price belongs to
    price_area           varchar(50)       NULL,
    dom_price_check      varchar(20)       NOT NULL,   -- match / match_flash_sale / not_visible / mismatch
    source_url           nvarchar(500)     NOT NULL,
    raw_file             nvarchar(300)     NOT NULL,   -- trace back to raw JSON
    row_id               nvarchar(200)     NOT NULL,
    CONSTRAINT CK_Obs_ListPrice CHECK (list_price_vnd IS NULL OR list_price_vnd >= sale_price_vnd),
    CONSTRAINT UQ_Obs_RunProduct UNIQUE (run_id, product_key)   -- one price per product per run
);
GO

IF OBJECT_ID('dbo.ProductMatches', 'U') IS NULL
CREATE TABLE dbo.ProductMatches (
    match_id               int IDENTITY(1,1) NOT NULL CONSTRAINT PK_ProductMatches PRIMARY KEY,
    run_id                 varchar(40)   NOT NULL CONSTRAINT FK_Match_Runs REFERENCES dbo.CollectionRuns(run_id),
    status                 varchar(15)   NOT NULL CONSTRAINT CK_Match_Status CHECK (status IN ('MATCHED', 'NEEDS_REVIEW')),
    reason                 nvarchar(300) NOT NULL,
    name_similarity        decimal(4,3)  NOT NULL,
    bhx_observation_id     char(20)      NOT NULL CONSTRAINT FK_Match_BhxObs REFERENCES dbo.PriceObservations(observation_id),
    winmart_observation_id char(20)      NOT NULL CONSTRAINT FK_Match_WmObs REFERENCES dbo.PriceObservations(observation_id),
    price_diff_vnd         decimal(12,0) NULL,         -- WinMart - BHX (MATCHED only)
    price_diff_pct         decimal(8,2)  NULL,         -- price_diff_vnd / BHX * 100
    price_comparable       bit           NOT NULL,
    CONSTRAINT UQ_Match_RunBhx UNIQUE (run_id, bhx_observation_id),
    CONSTRAINT UQ_Match_RunWm  UNIQUE (run_id, winmart_observation_id)   -- one-to-one
);
GO

IF OBJECT_ID('dbo.vw_PriceComparison', 'V') IS NULL
EXEC('CREATE VIEW dbo.vw_PriceComparison AS
SELECT m.run_id, pb.brand, pb.name AS bhx_name, pw.name AS winmart_name,
       pb.size_value, pb.size_unit, pb.pack_count,
       ob.sale_price_vnd AS bhx_price_vnd, ow.sale_price_vnd AS winmart_price_vnd,
       m.price_diff_vnd, m.price_diff_pct,
       ob.collected_at AS bhx_collected_at, ow.collected_at AS winmart_collected_at,
       pb.product_url AS bhx_url, pw.product_url AS winmart_url, pw.barcode AS winmart_barcode
FROM dbo.ProductMatches m
JOIN dbo.PriceObservations ob ON ob.observation_id = m.bhx_observation_id
JOIN dbo.PriceObservations ow ON ow.observation_id = m.winmart_observation_id
JOIN dbo.Products pb ON pb.product_key = ob.product_key
JOIN dbo.Products pw ON pw.product_key = ow.product_key
WHERE m.status = ''MATCHED'' AND m.price_comparable = 1');
GO
