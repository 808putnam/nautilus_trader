// -------------------------------------------------------------------------------------------------
//  Copyright (C) 2015-2023 Nautech Systems Pty Ltd. All rights reserved.
//  https://nautechsystems.io
//
//  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
//  You may not use this file except in compliance with the License.
//  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
//
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.
// -------------------------------------------------------------------------------------------------

use sqlx::{Executor, PgPool};
use scripts::db::database::{DbEngine, get_connection_string};
#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>>{
    let connection_string = get_connection_string(DbEngine::POSTGRES);
    let pool = PgPool::connect(&connection_string).await
        .map_err(|e| e.to_string())?;

    // scan all the files in the current directory
    let mut sql_files = std::fs::read_dir("../schema/sql")?
        .collect::<Result<Vec<_>, std::io::Error>>()?;


    pool.execute("
           DO $$BEGIN
   IF NOT EXISTS (
      SE`LECT FROM pg_roles
      WHERE rolname = 'nautilus'
   ) THEN
      CREATE ROLE "nautilus" PASSWORD 'pass' LOGIN;
   END IF;
END
$$;").await
        .map_err(|e| e.to_string())?;.
    for file in sql_files.iter_mut() {
        let file_name = file.file_name();
        println!("Executing SQL file: {:?}", file_name);
        let file_path = file.path();
        let sql_content = std::fs::read_to_string(file_path.clone())?;
        for sql_statement in sql_content.split(";").filter(|s| !s.trim().is_empty()) {
            sqlx::query(sql_statement)
                .execute(&pool)
                .await
                .map_err(|e| e.to_string())?;
        }
    }
    println!("Created nautilus schema and role.");
    Ok(())
}

